from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from core.schema import schema

import debug_toolbar

admin.site.site_header = 'PcStore Admin'
admin.site.index_title = 'Admin'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('store/', include('store.urls')),
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True, schema=schema))),
    path('__debug__/', include(debug_toolbar.urls)),
]
