from django.contrib import admin

# Override the default admin index template
admin.site.index_template = 'admin/custom_index.html'
