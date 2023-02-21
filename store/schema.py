from uuid import uuid4
from django.db.models import Q
from django.db import transaction
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django_filters import FilterSet, OrderingFilter
from graphql import GraphQLError
from .models import Cart, CartItem, Customer, Order, OrderItem, Product, Collection, Promotion

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


# Types Models

class PromotionType(DjangoObjectType):
    class Meta:
        model = Promotion
        fields = ('id', 'description', 'discount')


class CollectionType(DjangoObjectType):
    class Meta:
        model = Collection
        fields = ('id', 'title', 'featured_product')


class ProductType(DjangoObjectType):
    products_count = graphene.Int()
    products_collection_count = graphene.Int()
    index = graphene.Int()

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
            'products_count',
            'products_collection_count'
        )
        # filter_fields = ['collection__title', 'inventory']
        interfaces = (relay.Node, )

    def resolve_index(self, info):
        return self.pk

    def resolve_products_count(root, info):
        return len(Product.objects.all())

    def resolve_products_collection_count(root, info):
        return len(Product.objects.filter(collection__title=root.collection))


class CustomerType(DjangoObjectType):
    user_id = graphene.Int()

    class Meta:
        model = Customer
        fields = ('phone',
                  'birth_date',
                  'user_id')
        interfaces = (relay.Node, )


class CartItemType(DjangoObjectType):
    cart_id = graphene.UUID()
    product_id = graphene.Int()
    product = graphene.Field(ProductType)
    total_price = graphene.Decimal()
    index = graphene.Int()

    class Meta:
        model = CartItem
        fields = ['id', 'cart_id',
                  'product', 'quantity', 'total_price','index']
        interfaces = (relay.Node, )

    def resolve_product(root, info):
        return Product.objects.get(pk=root.product_id)

    def resolve_total_price(root, info):
        return root.quantity * Product.objects.get(pk=root.product_id).price

    def resolve_index(self, info):
        return self.pk

    def resolve_product_id(root, info):
        if not Product.objects.filter(pk=root.product_id).exists():
            raise GraphQLError("No product with the given ID was found !!")

        return root.product_id


class AddCartItemType(DjangoObjectType):
    cart_id = graphene.UUID()
    product_id = graphene.Int()
    index = graphene.Int()

    class Meta:
        model = CartItem
        fields = ['id', 'cart_id', 'product_id', 'quantity','index']
        interfaces = (relay.Node, )
    
    def resolve_index(self, info):
        return self.pk


class CartType(DjangoObjectType):
    id = graphene.UUID()
    items = graphene.List(CartItemType)
    total_price = graphene.Decimal()
    items_number = graphene.Int()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price']

    def resolve_items(root, info):
        return CartItem.objects.all().filter(cart_id=root.id)

    def resolve_total_price(root, info):
        items = CartItem.objects.all().filter(cart_id=root.id)
        if len(items) == 0:
            return "0"
        else:
            total_price = 0
            for item in items:
                total_price += item.quantity * item.product.price
            return total_price

    def resolve_items_number(root,info):
        items = CartItem.objects.all().filter(cart_id=root.id)
        items_number = 0
        for item in items:
            items_number += item.quantity
        return items_number



class OrderItemType(DjangoObjectType):
    order_id = graphene.Int()
    product_id = graphene.Int()
    product = graphene.Field(ProductType)

    class Meta:
        model = OrderItem
        fields = ['id', 'order_id', 'product',
                  'product_id', 'unit_price', 'quantity']


class OrderType(DjangoObjectType):
    customer_id = graphene.Int()
    customer = graphene.Field(CustomerType)
    items = graphene.List(OrderItemType)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'placed_at', 'payment_status', 'items']

    def resolve_items(root, info):
        return OrderItem.objects.filter(order_id=root.id)


class AddOrderType(DjangoObjectType):
    customer_id = graphene.Int()
    cart_id = graphene.UUID()

    class Meta:
        model = Order
        fields = ['id', 'customer_id', 'cart_id']


# Queries


class Query(graphene.ObjectType):
    promotions = graphene.List(PromotionType)
    promotion = graphene.Field(PromotionType, id=graphene.Int())

    collections = graphene.List(CollectionType)
    collection = graphene.Field(CollectionType, id=graphene.Int())

    products = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,
        search=graphene.String(),
        first=graphene.Int(),
        offset=graphene.Int(),
        limit=graphene.Int()
    )
    all_products = graphene.List(ProductType)
    product = graphene.Field(ProductType, id=graphene.Int())

    customers = graphene.List(CustomerType)
    customer = graphene.Field(CustomerType, id=graphene.Int())

    cart = graphene.Field(CartType, id=graphene.UUID())
    cart_items = graphene.List(
        CartItemType,
        cartId=graphene.UUID(),
    )
    cart_item = graphene.Field(CartItemType, id=graphene.Int())

    orders = graphene.List(OrderType)
    order = graphene.Field(OrderType, id=graphene.Int())
    order_items = graphene.List(OrderItemType)
    order_item = graphene.Field(OrderItemType, id=graphene.Int())

    def resolve_promotions(root, info, **kwargs):
        return Promotion.objects.all()

    def resolve_promotion(root, info, id):
        return Promotion.objects.get(pk=id)

    def resolve_collections(root, info, **kwargs):
        return Collection.objects.all()

    def resolve_collection(root, info, id):
        return Collection.objects.get(pk=id)

    def resolve_all_products(root, info, **kwargs):
        return Product.objects.all()

    def resolve_product(root, info, id):
        return Product.objects.get(pk=id)

    def resolve_products(self, info, search=None, **kwargs):
        if search:
            # filter = (Q(title__icontains=search) |
            #           Q(description__icontains=search))
            filter = Q(title__icontains=search)

            return Product.objects.all().filter(filter)

        return Product.objects.all()

    def resolve_customers(root, info):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')
        return Customer.objects.all()

    def resolve_customer(root, info, id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')
        return Customer.objects.get(pk=id)

    def resolve_cart(root, info, id):
        return Cart.objects.get(pk=id)

    def resolve_cart_items(root, info, cartId=None, **kwargs):
        if cartId:
            filter = Q(cart_id__exact=cartId)
            return CartItem.objects.all().filter(filter)
        return CartItem.objects.all()

    def resolve_cart_item(root, info, id):
        return CartItem.objects.get(pk=id)

    def resolve_orders(root, info):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        return Order.objects.all()

    def resolve_order(root, info, id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        return Order.objects.get(pk=id)

    def resolve_order_items(root, info):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        return OrderItem.objects.all()

    def resolve_order_item(root, info, id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        return OrderItem.objects.get(pk=id)

# Mutations


class CreateCustomer(graphene.Mutation):
    class Arguments:
        phone = graphene.String(required=True)
        birth_date = graphene.Date(required=True)
        user_id = graphene.Int(required=True)

    customer = graphene.Field(CustomerType)

    @classmethod
    def mutate(cls, root, info, phone, birth_date, user_id):
        customer = Customer()
        customer.phone = phone
        customer.birth_date = birth_date
        customer.user_id = user_id
        customer.save()

        return CreateCustomer(customer=customer)


class UpdateCustomer(graphene.Mutation):
    class Arguments:
        phone = graphene.String()
        birth_date = graphene.Date()
        id = graphene.ID()

    collection = graphene.Field(CollectionType)

    @classmethod
    def mutate(cls, root, info, phone,
               birth_date, id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")

        if user.id != int(id) and user.is_staff == False:
            raise Exception("Can't update other user !")

        customer = Customer.objects.get(pk=id)
        customer.phone = phone
        customer.birth_date = birth_date
        customer.save()

        return UpdateCustomer(customer=customer)


class DeleteCustomer(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    customer = graphene.Field(CustomerType)

    @classmethod
    def mutate(cls, root, info, id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        customer = Customer(pk=id)
        customer.delete()


class UpdateCollection(graphene.Mutation):
    class Arguments:
        # Mutation to update a collection
        title = graphene.String(required=True)
        id = graphene.ID()

    collection = graphene.Field(CollectionType)

    @classmethod
    def mutate(cls, root, info, title, id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        collection = Collection.objects.get(pk=id)
        collection.title = title
        collection.save()

        return UpdateCollection(collection=collection)


class CreateCollection(graphene.Mutation):
    class Arguments:
        # Mutation to create a collection
        title = graphene.String(required=True)

    # Class attributes define the response of the mutation
    collection = graphene.Field(CollectionType)

    @classmethod
    def mutate(cls, root, info, title):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        collection = Collection()
        collection.title = title
        collection.save()

        return CreateCollection(collection=collection)


class DeleteCollection(graphene.Mutation):
    class Arguments:
        # Mutation to update a collection
        id = graphene.ID()

    collection = graphene.Field(CollectionType)

    @classmethod
    def mutate(cls, root, info, id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        collection = Collection(pk=id)
        collection.delete()


class ProductInput(graphene.InputObjectType):
    title = graphene.String()
    description = graphene.JSONString()
    price = graphene.String()
    inventory = graphene.Int()
    slug = graphene.String()
    last_update = graphene.DateTime()
    # collection = graphene.ID()
    collection_id = graphene.Int(name="collection")
    images = graphene.JSONString()


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, input):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        product = Product()
        product.title = input.title
        product.description = input.description
        product.price = input.price
        product.inventory = input.inventory
        product.slug = input.slug
        product.last_update = input.last_update
        product.collection = input.collection_id
        product.images = input.images
        product.save()
        return CreateProduct(product=product)


class UpdateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)
        id = graphene.ID()

    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, input, id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        product = Product.objects.get(pk=id)
        product.title = input.title
        product.description = input.description
        product.price = input.price
        product.inventory = input.inventory
        product.slug = input.slug  # need function to sync input.title
        product.save()
        return UpdateProduct(product=product)


class DeleteProduct(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        product = Product(pk=id)
        product.delete()


class CreateCart(graphene.Mutation):
    class Arguments:
        name=graphene.String()

    cart = graphene.Field(CartType)

    @classmethod
    def mutate(cls, root, info,name):
        cart = Cart()
        cart.id = uuid4()
        cart.save()

        return CreateCart(cart=cart)


class DeleteCart(graphene.Mutation):
    class Arguments:
        id = graphene.UUID()

    cart = graphene.Field(CartType)

    @classmethod
    def mutate(cls, root, info, id):
        cart = Cart(pk=id)
        cart.delete()


class CreateCartItem(graphene.Mutation):
    class Arguments:
        cart_id = graphene.UUID(required=True)
        product_id = graphene.Int(required=True)
        quantity = graphene.Int(required=True)

    cart_item = graphene.Field(AddCartItemType)

    @classmethod
    def mutate(cls, root, info, cart_id,
               product_id, quantity):
        try:
            cart_item = CartItem.objects.get(
                cart_id=cart_id, product_id=product_id)
            cart_item.quantity += quantity
            cart_item.save()
        except CartItem.DoesNotExist:
            cart_item = CartItem()
            cart_item.cart_id = cart_id
            cart_item.product_id = product_id
            cart_item.quantity = quantity
            cart_item.save()

        return CreateCartItem(cart_item=cart_item)


class UpdateCartItem(graphene.Mutation):
    class Arguments:
        quantity = graphene.Int(required=True)
        id = graphene.ID()

    cart_item = graphene.Field(CartItemType)

    @classmethod
    def mutate(cls, root, info, quantity, id):
        cart_item = CartItem.objects.get(pk=id)
        cart_item.quantity = quantity
        cart_item.save()

        return UpdateCartItem(cart_item=cart_item)


class DeleteCartItem(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    cart_item = graphene.Field(CartItemType)

    @classmethod
    def mutate(cls, root, info, id):
        cart_item = CartItem(pk=id)
        cart_item.delete()


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.Int(required=True)
        cart_id = graphene.UUID(required=True)

    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, cart_id,
               customer_id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")

        with transaction.atomic():
            # Validate cart_id
            if not Cart.objects.filter(pk=cart_id).exists():
                raise GraphQLError('No cart with the given ID was found !!!')
            if CartItem.objects.filter(calendar=cart_id).count() == 0:
                raise GraphQLError('The cart is empty !!!')
            # Create Order
            order = Order()
            order.customer_id = customer_id
            order.save()
            # Create Order Items
            cart_items = CartItem.objects.select_related(
                'product').filter(cart_id=cart_id)
            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    unit_price=item.product.price,
                    quantity=item.quantity
                ) for item in cart_items
            ]
            OrderItem.objects.bulk_create(order_items)
            # Delete cart item
            Cart.objects.filter(pk=cart_id).delete()

            return CreateOrder(order=order)


class UpdateOrder(graphene.Mutation):
    class Arguments:
        id = graphene.ID()
        payment_status = graphene.String(required=True)

    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, payment_status, id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        order = Order.objects.get(pk=id)
        order.payment_status = payment_status
        order.save()

        return UpdateOrder(order=order)


class DeleteOrder(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, id):
        # Check permission
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication credentials were not provided !")
        if not user.is_staff:
            raise Exception('Not Authorized!')

        order = Order(pk=id)
        order_items = OrderItem.objects.filter(order_id=id)
        order_items.delete()
        order.delete()


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    update_customer = UpdateCustomer.Field()
    delete_customer = DeleteCustomer.Field()
    create_collection = CreateCollection.Field()
    update_collection = UpdateCollection.Field()
    delete_collection = DeleteCollection.Field()
    create_product = CreateProduct.Field()
    update_product = UpdateProduct.Field()
    delete_product = DeleteProduct.Field()
    create_cart = CreateCart.Field()
    delete_cart = DeleteCart.Field()
    create_cart_item = CreateCartItem.Field()
    update_cart_item = UpdateCartItem.Field()
    delete_cart_item = DeleteCartItem.Field()
    create_order = CreateOrder.Field()
    update_order = UpdateOrder.Field()
    delete_order = DeleteOrder.Field()


# schema = graphene.Schema(query=Query, mutation=Mutation)
