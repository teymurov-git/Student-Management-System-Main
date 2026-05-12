from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from attendance.models import AttendanceRecord
from payments.models import MonthlyPayment
from students.models import Student, StudentGroup


def _wire_widgets(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        c = field.widget.attrs.get("class", "").strip()
        field.widget.attrs["class"] = f"{c} field-control".strip()


class PortalAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _wire_widgets(self)


class StudentGroupForm(forms.ModelForm):
    lesson_weekdays = forms.MultipleChoiceField(
        choices=StudentGroup.LESSON_WEEKDAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Dərs günləri",
        help_text="Seçilən günlərdə hər həftə dərs keçiriləcək. Heç nə seçilməsə, davamiyyət cədvəli ayın bütün günlərini göstərəcək.",
    )

    class Meta:
        model = StudentGroup
        fields = ["name", "monthly_fee", "lesson_weekdays"]
        labels = {
            "name": "Qrup adı",
            "monthly_fee": "Aylıq məbləğ (₼)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and self.instance.pk:
            self.initial["lesson_weekdays"] = [
                str(value) for value in self.instance.lesson_weekday_numbers
            ]
        _wire_widgets(self)

    def clean_lesson_weekdays(self) -> str:
        return StudentGroup.normalize_lesson_weekdays(
            self.cleaned_data["lesson_weekdays"]
        )


class StudentGroupQuickForm(StudentGroupForm):
    pass


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "first_name",
            "last_name",
            "father_name",
            "phone",
            "parent_phone",
            "student_group",
            "monthly_tuition",
            "registration_date",
            "status",
            "notes",
        ]
        help_texts = {
            "parent_phone": "İstəyə bağlı.",
            "monthly_tuition": "Əgər 0 olarsa, seçilmiş qrupun aylıq ödənişi istifadə olunur.",
            "notes": "Daxili qeydlər, yalnız admin üçün.",
        }
        widgets = {
            "registration_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student_group"].queryset = StudentGroup.objects.all().order_by("name")
        self.fields["student_group"].required = False
        _wire_widgets(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.student_group_id:
            instance.class_group = instance.student_group.name
        else:
            instance.class_group = ""
        if commit:
            instance.save()
        return instance


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ["student", "date", "status", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.TextInput(attrs={"placeholder": "Qeyd (istəyə bağlı)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = Student.objects.filter(
            is_archived=False
        ).select_related("student_group").order_by("last_name", "first_name")
        _wire_widgets(self)


class MonthlyPaymentForm(forms.ModelForm):
    class Meta:
        model = MonthlyPayment
        fields = [
            "student",
            "month",
            "year",
            "amount",
            "payment_date",
            "status",
            "discount",
            "remaining_debt",
            "payment_method",
            "notes",
        ]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = Student.objects.select_related(
            "student_group"
        ).all().order_by("last_name", "first_name")
        _wire_widgets(self)

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.user and self.user.is_authenticated:
            obj.received_by = self.user
        if commit:
            obj.save()
        return obj
