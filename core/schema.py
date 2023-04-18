import re
from urllib.request import Request
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from django_filters import FilterSet, OrderingFilter

from graphql import GraphQLError
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import graphql_jwt
from graphql_auth.schema import UserQuery, MeQuery
from graphql_auth import mutations
from django.core.cache import cache

from store.models import Product, Promotion
from tags.models import Tag, TaggedItem
from .models import User
from store.schema import Query as StoreQuery, Mutation as StoreMutation
from tags.schema import Query as TagsQuery

from django.contrib.contenttypes.models import ContentType


def checkEmail(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    if(re.fullmatch(regex, email)):
        return True

    else:
        return False


# Filters


class ProductFilter(FilterSet):
    class Meta:
        model = Product
        fields = {
            'collection__title': ['exact'],
            'price': ['gt', 'lt'],
            'inventory': ['gt', 'lt']
        }

    order_by = OrderingFilter(
        fields=(
            ('title', 'title'),
            ('price', 'price'),
            ('inventory', 'inventory'),
            ('last_update', 'last_update'),
        )
    )


# Models
class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'verified',
                  'password', 'first_name', 'last_name', 'is_staff')


class TagItemType(DjangoObjectType):
    class Meta:
        model = Tag
        fields = ('id', 'label')


class ProductTagsType(DjangoObjectType):
    tags = graphene.List(TagItemType)

    class Meta:
        model = Product
        fields = ('id', 'title','tags')

    def resolve_tags(root, info):
        queryset = TaggedItem.objects.all().filter(object_id=root.id)
        product_tags = []
        for item in queryset:
            product_tags.append(Tag.objects.get(pk=item.tag_id))
        return product_tags


class FullProductType(DjangoObjectType):
    products_count = graphene.Int()
    products_collection_count = graphene.Int()
    index = graphene.Int()
    tags = graphene.List(TagItemType)

    class Meta:
        model = Product
        fields = (
            'id',
            'index',
            'title',
            'description',
            'price',
            'inventory',
            'slug',
            'last_update',
            'collection',
            'images',
            'promotions',
            'tags',
            'products_count',
            'products_collection_count'
        )
        # filter_fields = ['collection__title', 'inventory']
        interfaces = (relay.Node, )

    def resolve_products_count(root, info):
        return len(Product.objects.all())

    def resolve_products_collection_count(root, info):
        return len(Product.objects.filter(collection__title=root.collection))

    def resolve_index(self, info):
        return self.pk

    def resolve_tags(root, info):
        queryset = TaggedItem.objects.all().filter(object_id=root.id)
        product_tags = []
        for item in queryset:
            product_tags.append(Tag.objects.get(pk=item.tag_id))
        return product_tags

# Queries


class CoreQuery(graphene.ObjectType):
    users = graphene.List(UserType)
    user = graphene.Field(UserType, id=graphene.Int())
    me = graphene.Field(UserType)

    product_tags = graphene.Field(ProductTagsType, id=graphene.Int())

    full_products = DjangoFilterConnectionField(
        FullProductType,
        filterset_class=ProductFilter,
        search=graphene.String(),
        first=graphene.Int(),
        offset=graphene.Int(),
        limit=graphene.Int()
    )

    full_product = graphene.Field(FullProductType, id=graphene.Int())

    def resolve_users(root, info):
        user = info.context.user
        # if user.is_anonymous:
        #     raise Exception('Not logged in!')
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')
        return User.objects.all()

    def resolve_user(root, info, id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')
        return User.objects.get(pk=id)

    def resolve_me(root, info):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        return user

    def resolve_product_tags(root, info, id):
        return Product.objects.get(pk=id)

    def resolve_full_products(self, info, search=None, **kwargs):
        # Check if the result is already cached
        cache_key = "cached-products"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            print("cached_result lenght: ", len(cached_result))
            print("cached_result : ",cached_result)
            return cached_result

        # If the result is not cached, fetch it from the database
        if search:
            # filter = (Q(title__icontains=search) |
            #           Q(description__icontains=search))
            filter = Q(title__icontains=search)

            result = Product.objects.prefetch_related('promotions').all().filter(filter)

        result = Product.objects.prefetch_related('promotions').all()

        # Cache the result
        cache.set(cache_key, result, 60*60*5)

        return result

    def resolve_full_product(root, info, id):
        return Product.objects.get(pk=id)


class Query(
    StoreQuery,
    CoreQuery,
    TagsQuery,
    # UserQuery,
    # MeQuery,
    graphene.ObjectType,
):
    pass

# Mutations


class CreateUserInput(graphene.InputObjectType):
    username = graphene.String(required=True)
    first_name = graphene.String(default_value="")
    last_name = graphene.String(default_value="")
    email = graphene.String(required=True)
    password = graphene.String(required=True)
    verified = graphene.Boolean(default_value=False)


class UpdateUserInput(graphene.InputObjectType):
    username = graphene.String(required=False)
    first_name = graphene.String(required=False)
    last_name = graphene.String(required=False)
    email = graphene.String(required=False)
    password = graphene.String(required=False)
    verified = graphene.Boolean(required=False)
    is_staff = graphene.Boolean(required=False)


class CreateUser(graphene.Mutation):
    class Arguments:
        input = CreateUserInput(required=True)

    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, input):
        if not checkEmail(input.email):
            raise GraphQLError('Invalid Email !')
        else:
            validate_password(input.password)
            user = User()
            user.username = input.username
            user.first_name = input.first_name
            user.last_name = input.last_name
            user.email = input.email
            user.password = make_password(input.password)
            user.save()
            return CreateUser(user=user)

# PATCH User


class UpdateUser(graphene.Mutation):
    class Arguments:
        input = UpdateUserInput()
        id = graphene.ID()

    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, id, **kwargs):
        current_user = info.context.user
        if not current_user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")

        if current_user.id != int(id) and current_user.is_staff == False:
            raise Exception("Can't update other user !")

        user = User.objects.get(pk=id)

        for key, value in kwargs['input'].items():
            if (key == "email"):
                if not checkEmail(value):
                    raise GraphQLError('Invalid Email !')
                else:
                    setattr(user, key, value)

            if(key == "password"):
                validate_password(value)
                setattr(user, key, make_password(value))
            else:
                setattr(user, key, value)
        user.save()
        return CreateUser(user=user)


class DeleteUser(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    user = graphene.Field(UserType)

    @classmethod
    def mutate(cls, root, info, id):
        current_user = info.context.user
        if not current_user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not current_user.is_staff:
            raise Exception('Not Authorized!')

        user = User(pk=id)
        user.delete()


class CoreMutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()
    delete_user = DeleteUser.Field()
    login = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    register = mutations.Register.Field()


class Mutation(StoreMutation, CoreMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
