from django.contrib import admin

from .models import Application, Participant


class ParticipantInline(admin.TabularInline):
	model = Participant
	extra = 0
	min_num = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
	change_list_template = 'admin/applications/application/change_list.html'
	list_display = (
		'id',
		'tour_group',
		'contact_name',
		'contact_phone',
		'gender',
		'adult_count',
		'child_count',
		'deposit_amount',
		'balance_paid',
		'status',
		'created_at',
	)
	list_filter = ('status', 'deposit_paid', 'balance_paid', 'gender', 'created_at', 'tour_group')
	search_fields = ('contact_name', 'contact_phone', 'email', 'tour_group__code')
	autocomplete_fields = ('tour_group',)
	inlines = (ParticipantInline,)
	fieldsets = (
		('团信息', {'fields': ('tour_group',)}),
		('申请人信息', {
			'fields': (
				'contact_name', 'gender', 'birth_date', 'contact_phone',
				'contact_address', 'email', 'postal_code'
			)
		}),
		('紧急联系人', {
			'fields': (
				'emergency_contact_name', 'emergency_contact_relation',
				'emergency_contact_address', 'emergency_contact_phone'
			)
		}),
		('旅行人数', {'fields': ('adult_count', 'child_count')}),
		('订金信息', {
			'fields': (
				'deposit_paid', 'deposit_amount', 'deposit_receipt_no', 'deposit_paid_at'
			)
		}),
		('余款信息', {
			'fields': (
				'balance_paid', 'balance_amount', 'balance_receipt_no',
				'balance_paid_at', 'balance_due_date'
			)
		}),
		('取消信息', {
			'fields': ('status', 'canceled_at', 'refund_amount'),
			'classes': ('collapse',)
		}),
	)
	readonly_fields = ('created_at',)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
	list_display = ('full_name', 'id_card', 'application', 'is_contact')
	list_filter = ('is_contact',)
	search_fields = ('full_name', 'id_card', 'application__contact_name', 'application__tour_group__code')
	autocomplete_fields = ('application',)
