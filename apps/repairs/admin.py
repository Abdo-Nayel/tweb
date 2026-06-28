from django.contrib import admin
from .models import RepairOrder, RepairPart, RepairPayment

admin.site.register(RepairOrder)
admin.site.register(RepairPart)
admin.site.register(RepairPayment)
