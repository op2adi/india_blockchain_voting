from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Election, ElectionConstituency
from users.models import Constituency, State

class ElectionAdminForm(forms.ModelForm):
    all_constituencies = forms.BooleanField(
        required=False, 
        label=_('Select All Constituencies'),
        help_text=_('Check this box to include all constituencies in this election')
    )
    
    # Hidden field to track if the form was submitted with election type
    election_setup_complete = forms.BooleanField(required=False, widget=forms.HiddenInput())
    
    # Split datetime fields for better date/time picker support
    nomination_start_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    nomination_start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    nomination_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    nomination_end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    voting_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    voting_start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    voting_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    voting_end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    
    class Meta:
        model = Election
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if isinstance(field, forms.BooleanField):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        
        # If we're editing an existing object, set the initial values
        if self.instance and self.instance.pk:
            state = self.instance.state
            if state:
                # Check if all constituencies from this state are included
                state_constituencies = Constituency.objects.filter(state=state).count()
                election_constituencies = ElectionConstituency.objects.filter(
                    election=self.instance, 
                    constituency__state=state
                ).count()
                
                if state_constituencies == election_constituencies:
                    self.fields['all_constituencies'].initial = True
            else:
                # Check if all constituencies are included
                total_constituencies = Constituency.objects.count()
                election_constituencies = ElectionConstituency.objects.filter(
                    election=self.instance
                ).count()
                
                if total_constituencies == election_constituencies:
                    self.fields['all_constituencies'].initial = True
            
            # Set initial date and time values from the datetime fields
            if self.instance.nomination_start_date:
                self.fields['nomination_start_date'].initial = self.instance.nomination_start_date.date()
                self.fields['nomination_start_time'].initial = self.instance.nomination_start_date.time()
            
            if self.instance.nomination_end_date:
                self.fields['nomination_end_date'].initial = self.instance.nomination_end_date.date()
                self.fields['nomination_end_time'].initial = self.instance.nomination_end_date.time()
            
            if self.instance.voting_start_date:
                self.fields['voting_start_date'].initial = self.instance.voting_start_date.date()
                self.fields['voting_start_time'].initial = self.instance.voting_start_date.time()
                
            if self.instance.voting_end_date:
                self.fields['voting_end_date'].initial = self.instance.voting_end_date.date()
                self.fields['voting_end_time'].initial = self.instance.voting_end_date.time()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Combine date and time fields into datetime fields if both are provided
        date_time_pairs = [
            ('nomination_start_date', 'nomination_start_time', 'nomination_start_date'),
            ('nomination_end_date', 'nomination_end_time', 'nomination_end_date'),
            ('voting_start_date', 'voting_start_time', 'voting_start_date'),
            ('voting_end_date', 'voting_end_time', 'voting_end_date'),
        ]
        
        from datetime import datetime, time
        from django.utils import timezone
        import pytz
        
        for date_field, time_field, target_field in date_time_pairs:
            date_value = cleaned_data.get(date_field)
            time_value = cleaned_data.get(time_field)
            
            if date_value and time_value:
                # If we have both date and time, combine them
                dt = datetime.combine(date_value, time_value)
                # Make timezone aware
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                cleaned_data[target_field] = dt
            elif date_value and not time_value:
                # If we have only date, use midnight
                dt = datetime.combine(date_value, time.min)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                cleaned_data[target_field] = dt
        
        # Process the election type selection
        if 'election_type' in cleaned_data and cleaned_data['election_type'] == 'NATIONAL':
            # For national elections, ensure all_constituencies is checked and state is None
            cleaned_data['all_constituencies'] = True
            cleaned_data['state'] = None
        elif 'election_type' in cleaned_data and cleaned_data['election_type'] == 'STATE':
            # For state elections, need to ensure a state is selected
            if not cleaned_data.get('state'):
                self.add_error('state', 'For state elections, you must select a state.')
            else:
                # For state elections, all constituencies in that state
                cleaned_data['all_constituencies'] = True
        
        return cleaned_data
