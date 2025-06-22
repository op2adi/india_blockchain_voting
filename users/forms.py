from django import forms
from django.forms import DateInput
from django.core.validators import RegexValidator
from .models import Voter, State, Constituency

class VoterRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirm Password")
    
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    voter_id = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), 
                              validators=[RegexValidator(regex=r'^[A-Z]{3}\d{7}$',
                                         message='Voter ID must be in format: ABC1234567')])
    
    state = forms.ModelChoiceField(
        queryset=State.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-control form-select', 'id': 'id_state_select'}),
        empty_label="Select State",
        required=True
    )
    
    constituency = forms.ModelChoiceField(
        queryset=Constituency.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control form-select', 'id': 'id_constituency_select'}),
        empty_label="Select Constituency",
        required=True
    )
    
    date_of_birth = forms.DateField(
        widget=DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    
    gender = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        widget=forms.Select(attrs={'class': 'form-control form-select'}),
        required=True
    )
    
    mobile_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[RegexValidator(regex=r'^\+91\d{10}$', message='Mobile number must be +91 followed by 10 digits')]
    )
    
    address_line1 = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    address_line2 = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    city = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    pincode = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[RegexValidator(regex=r'^\d{6}$', message='Pincode must be 6 digits')]
    )

    class Meta:
        model = Voter
        fields = ('first_name', 'last_name', 'email', 'voter_id', 'state', 'constituency',  
                 'date_of_birth', 'gender', 'mobile_number', 'address_line1', 
                 'address_line2', 'city', 'pincode')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If instance has a state, populate constituencies dropdown
        if 'instance' in kwargs and kwargs['instance'] and kwargs['instance'].state:
            self.fields['constituency'].queryset = Constituency.objects.filter(
                state=kwargs['instance'].state
            ).order_by('name')
            
        # If initial state provided in POST data, populate constituencies
        if args and len(args) > 0 and 'state' in args[0]:
            try:
                state_id = int(args[0]['state'])
                self.fields['constituency'].queryset = Constituency.objects.filter(
                    state_id=state_id
                ).order_by('name')
            except (ValueError, TypeError):
                pass

    def clean_confirm_password(self):
        password = self.cleaned_data.get("password")
        confirm_password = self.cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        return confirm_password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        # Set default values for required fields
        user.encrypted_voter_card_number = 'encrypted_placeholder'
        
        if commit:
            user.save()
            if self.cleaned_data.get('profile_picture'):
                # Handle profile picture in a separate model if needed
                pass
        return user
