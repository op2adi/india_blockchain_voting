// Election form enhancements
document.addEventListener('DOMContentLoaded', function() {
    // Elements for constituency selection
    const selectAllBtn = document.getElementById('selectAllBtn');
    const deselectAllBtn = document.getElementById('deselectAllBtn');
    const filterByStateBtn = document.getElementById('filterByStateBtn');
    const stateFilter = document.getElementById('stateFilter');
    // Try to get the all_constituencies selector with different possible IDs
    const allConstituenciesSelect = 
        document.getElementById('id_all_constituencies') || 
        document.querySelector('[name="all_constituencies"]');
    const stateSelect = document.getElementById('id_state');
    const constituencySelector = document.getElementById('constituencySelector');
    
    // Elements for election type selection
    const nationalRadio = document.getElementById('election_type_national');
    const stateRadio = document.getElementById('election_type_state');
    const customRadio = document.getElementById('election_type_custom');
    const stateSelector = document.getElementById('state_selector');
    
    // Elements for date pickers
    const nominationStartDateBtn = document.getElementById('nomination_start_date_btn');
    const nominationStartTimeBtn = document.getElementById('nomination_start_time_btn');
    const nominationEndDateBtn = document.getElementById('nomination_end_date_btn');
    const nominationEndTimeBtn = document.getElementById('nomination_end_time_btn');
    const votingStartDateBtn = document.getElementById('voting_start_date_btn');
    const votingStartTimeBtn = document.getElementById('voting_start_time_btn');
    const votingEndDateBtn = document.getElementById('voting_end_date_btn');
    const votingEndTimeBtn = document.getElementById('voting_end_time_btn');
    
    console.log("Election form script loaded");
    
    // Initialize election type controls
    if (nationalRadio && stateRadio && customRadio) {
        console.log("Election type radios found");
        
        // Default to national if nothing selected
        if (!nationalRadio.checked && !stateRadio.checked && !customRadio.checked) {
            nationalRadio.checked = true;
        }
        
        // Election type change handlers
        nationalRadio.addEventListener('change', function() {
            if (this.checked) {
                console.log("National election selected");
                if (stateSelector) stateSelector.style.display = 'none';
                if (constituencySelector) constituencySelector.style.display = 'none';
                if (allConstituenciesCheckbox) allConstituenciesCheckbox.checked = true;
            }
        });
        
        stateRadio.addEventListener('change', function() {
            if (this.checked) {
                console.log("State election selected");
                if (stateSelector) stateSelector.style.display = 'block';
                if (constituencySelector) constituencySelector.style.display = 'none';
                if (allConstituenciesCheckbox) allConstituenciesCheckbox.checked = false;
            }
        });
        
        customRadio.addEventListener('change', function() {
            if (this.checked) {
                console.log("Custom election selected");
                if (stateSelector) stateSelector.style.display = 'none';
                if (constituencySelector) constituencySelector.style.display = 'block';
                if (allConstituenciesCheckbox) allConstituenciesCheckbox.checked = false;
            }
        });
        
        // Trigger change event based on current selection
        if (nationalRadio.checked) nationalRadio.dispatchEvent(new Event('change'));
        else if (stateRadio.checked) stateRadio.dispatchEvent(new Event('change'));
        else if (customRadio.checked) customRadio.dispatchEvent(new Event('change'));
        else {
            // Default to national
            nationalRadio.checked = true;
            nationalRadio.dispatchEvent(new Event('change'));
        }
    } else {
        console.log("Election type radios not found");
    }
    
    // Constituency selection buttons
    if (selectAllBtn && allConstituenciesSelect) {
        console.log("Select all button found");
        selectAllBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // Select all options in the multi-select
            if (allConstituenciesSelect.options) {
                for (let i = 0; i < allConstituenciesSelect.options.length; i++) {
                    allConstituenciesSelect.options[i].selected = true;
                }
            }
            console.log("All constituencies selected");
        });
    }
    
    if (deselectAllBtn && allConstituenciesSelect) {
        console.log("Deselect all button found");
        deselectAllBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // Deselect all options in the multi-select
            if (allConstituenciesSelect.options) {
                for (let i = 0; i < allConstituenciesSelect.options.length; i++) {
                    allConstituenciesSelect.options[i].selected = false;
                }
            }
            console.log("All constituencies deselected");
        });
    }
    
    // Date and time picker buttons
    if (nominationStartDateBtn) {
        nominationStartDateBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('id_nomination_start_date').focus();
            document.getElementById('id_nomination_start_date').showPicker();
        });
    }
    
    if (nominationStartTimeBtn) {
        nominationStartTimeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('id_nomination_start_time').focus();
            document.getElementById('id_nomination_start_time').showPicker();
        });
    }
    
    if (nominationEndDateBtn) {
        nominationEndDateBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('id_nomination_end_date').focus();
            document.getElementById('id_nomination_end_date').showPicker();
        });
    }
    
    if (nominationEndTimeBtn) {
        nominationEndTimeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('id_nomination_end_time').focus();
            document.getElementById('id_nomination_end_time').showPicker();
        });
    }
    
    if (votingStartDateBtn) {
        votingStartDateBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('id_voting_start_date').focus();
            document.getElementById('id_voting_start_date').showPicker();
        });
    }
    
    if (votingStartTimeBtn) {
        votingStartTimeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('id_voting_start_time').focus();
            document.getElementById('id_voting_start_time').showPicker();
        });
    }
    
    if (votingEndDateBtn) {
        votingEndDateBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('id_voting_end_date').focus();
            document.getElementById('id_voting_end_date').showPicker();
        });
    }
    
    if (votingEndTimeBtn) {
        votingEndTimeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('id_voting_end_time').focus();
            document.getElementById('id_voting_end_time').showPicker();
        });
    }
    
    if (filterByStateBtn && stateFilter && allConstituenciesSelect) {
        console.log("Filter by state button found");
        filterByStateBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const selectedState = stateFilter.value;
            if (selectedState) {
                // First deselect all
                if (deselectAllBtn) {
                    deselectAllBtn.click();
                } else if (allConstituenciesSelect && allConstituenciesSelect.options) {
                    for (let i = 0; i < allConstituenciesSelect.options.length; i++) {
                        allConstituenciesSelect.options[i].selected = false;
                    }
                }
                
                // Then select only constituencies in this state
                if (allConstituenciesSelect && allConstituenciesSelect.options) {
                    for (let i = 0; i < allConstituenciesSelect.options.length; i++) {
                        const option = allConstituenciesSelect.options[i];
                        if (option.text.includes(`State: ${selectedState}`)) {
                            option.selected = true;
                        }
                    }
                }
                
                // Set the state in the state dropdown if available
                if (stateSelect) {
                    stateSelect.value = selectedState;
                    // Trigger state change
                    stateSelect.dispatchEvent(new Event('change'));
                }
                
                console.log("Filtered by state: " + selectedState);
            }
        });
    }
    
    // Add onclick handlers for date/time picker buttons
    function setupDateTimePickerButtons() {
        const dateTimeFields = [
            'nomination_start', 'nomination_end', 
            'voting_start', 'voting_end'
        ];
        
        dateTimeFields.forEach(field => {
            const dateBtn = document.getElementById(`${field}_date_btn`);
            const timeBtn = document.getElementById(`${field}_time_btn`);
            const dateField = document.getElementById(`id_${field}_date`);
            const timeField = document.getElementById(`id_${field}_time`);
            
            if (dateBtn && dateField) {
                dateBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    dateField.showPicker();
                });
            }
            
            if (timeBtn && timeField) {
                timeBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    timeField.showPicker();
                });
            }
        });
    }
    
    // Set up date time fields with initial values
    function setupDateTimeFields() {
        // Default date values
        const now = new Date();
        const today = now.toISOString().split('T')[0];
        
        // Date fields
        const dateFields = {
            'id_nomination_start_date': today,
            'id_nomination_end_date': new Date(now.setDate(now.getDate() + 14)).toISOString().split('T')[0], // +14 days
            'id_voting_start_date': new Date(now.setDate(now.getDate() + 16)).toISOString().split('T')[0], // +16 days
            'id_voting_end_date': new Date(now.setDate(now.getDate() + 17)).toISOString().split('T')[0] // +1 day
        };
        
        // Time fields
        const timeFields = {
            'id_nomination_start_time': '08:00',
            'id_nomination_end_time': '17:00',
            'id_voting_start_time': '08:00',
            'id_voting_end_time': '17:00'
        };
        
        // Set default values if empty
        Object.keys(dateFields).forEach(id => {
            const field = document.getElementById(id);
            if (field && !field.value) {
                field.value = dateFields[id];
            }
        });
        
        Object.keys(timeFields).forEach(id => {
            const field = document.getElementById(id);
            if (field && !field.value) {
                field.value = timeFields[id];
            }
        });
    }
    
    // Initialize date/time fields and buttons
    setupDateTimeFields();
    setupDateTimePickerButtons();
});
