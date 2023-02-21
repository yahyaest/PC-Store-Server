import graphene
from graphene_django import DjangoObjectType
from .models import Tag, TaggedItem


class TagType(DjangoObjectType):
    class Meta:
        model = Tag
        fields = ('id', 'label')


class TaggedItemType(DjangoObjectType):
    class Meta:
        model = TaggedItem
        fields = ('id', 'object_id', 'tag')
   

class Query(graphene.ObjectType):
    tags = graphene.List(TagType)
    tag = graphene.Field(TagType, id=graphene.Int())

    tagged_items = graphene.List(TaggedItemType)
    tagged_item = graphene.Field(TaggedItemType, id=graphene.Int())

    def resolve_tags(root, info, **kwargs):
        return Tag.objects.all()

    def resolve_tag(root, info, id):
        return Tag.objects.get(pk=id)

    def resolve_tagged_items(root, info, **kwargs):
        return TaggedItem.objects.all()

    def resolve_tagged_item(root, info, id):
        return TaggedItem.objects.get(pk=id)
