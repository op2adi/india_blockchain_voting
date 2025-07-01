/**
 * Enhanced Admin UI for India Blockchain Voting System
 * Includes security features, UX improvements, and blockchain integration
 */

document.addEventListener('DOMContentLoaded', function() {
    // Add Bootstrap classes to elements
    enhanceFormFields();
    enhanceButtons();
    enhanceInlineGroups();
    
    // Special handling for the all_constituencies checkbox
    setupAllConstituenciesOption();
    
    // Add security features
    preventBackNavigation();
    setupSessionTimeout();
    
    // Add blockchain visualizations if on relevant pages
    setupBlockchainVisualizations();
    
    // Enhance dashboard cards and stats
    enhanceDashboardElements();
});

/**
 * Add Bootstrap classes and styling to form fields
 */
function enhanceFormFields() {
    // Add Bootstrap classes to form controls
    document.querySelectorAll('input[type="text"], input[type="password"], input[type="email"], input[type="url"], input[type="number"], textarea, select').forEach(function(element) {
        element.classList.add('form-control');
    });
    
    // Style checkbox inputs
    document.querySelectorAll('input[type="checkbox"]').forEach(function(element) {
        element.classList.add('form-check-input');
        
        // Create wrapper if doesn't exist
        const parent = element.parentNode;
        if (parent.tagName !== 'DIV' || !parent.classList.contains('form-check')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'form-check';
            parent.insertBefore(wrapper, element);
            wrapper.appendChild(element);
            
            // If there's a label, move it inside the wrapper
            const label = parent.querySelector('label[for="' + element.id + '"]');
            if (label) {
                label.classList.add('form-check-label');
                wrapper.appendChild(label);
            }
        }
    });
    
    // Style radio buttons
    document.querySelectorAll('input[type="radio"]').forEach(function(element) {
        element.classList.add('form-check-input');
    });
}

/**
 * Enhance buttons with Bootstrap classes
 */
function enhanceButtons() {
    // Primary buttons
    document.querySelectorAll('input[type="submit"], input.default').forEach(function(element) {
        element.classList.add('btn', 'btn-primary');
    });
    
    // Secondary buttons
    document.querySelectorAll('input[type="button"], a.button').forEach(function(element) {
        element.classList.add('btn', 'btn-secondary');
    });
}

/**
 * Enhance inline form groups (for admin inlines)
 */
function enhanceInlineGroups() {
    document.querySelectorAll('.inline-group').forEach(function(group) {
        group.classList.add('card', 'mb-3');
        
        const header = group.querySelector('h2');
        if (header) {
            header.classList.add('card-header');
        }
        
        const formset = group.querySelector('.inline-formset');
        if (formset) {
            formset.classList.add('card-body');
        }
    });
}

/**
 * Setup special behavior for the "All Constituencies" option in the election form
 */
function setupAllConstituenciesOption() {
    const allConstituenciesCheckbox = document.getElementById('id_all_constituencies');
    if (!allConstituenciesCheckbox) return;
    
    const stateSelect = document.getElementById('id_state');
    const inlineGroup = document.querySelector('.inline-group');
    
    // Function to update help text based on state selection
    function updateHelpText() {
        const helpText = document.querySelector('.help');
        if (!helpText) return;
        
        if (stateSelect && stateSelect.value) {
            const stateName = stateSelect.options[stateSelect.selectedIndex].text;
            helpText.textContent = `Select all constituencies in ${stateName}`;
        } else {
            helpText.textContent = 'Select all constituencies in India';
        }
    }
    
    // Toggle visibility of the constituencies inline when "All" is checked
    allConstituenciesCheckbox.addEventListener('change', function() {
        if (this.checked && inlineGroup) {
            inlineGroup.style.display = 'none';
        } else if (inlineGroup) {
            inlineGroup.style.display = 'block';
        }
    });
    
    // Update help text when state changes
    if (stateSelect) {
        stateSelect.addEventListener('change', updateHelpText);
    }
    
    // Initial setup
    updateHelpText();
    
    // Initial visibility
    if (allConstituenciesCheckbox.checked && inlineGroup) {
        inlineGroup.style.display = 'none';
    }
}

/**
 * Prevent back button navigation after logout for security
 * This is critical for preventing unauthorized access to sensitive information
 */
function preventBackNavigation() {
    // Check if we're on a login page or if there's a logout parameter
    const isLoggedOut = window.location.href.includes('login') || 
                         window.location.href.includes('logout=1');
    
    if (isLoggedOut) {
        // Mark this as a page that shouldn't be accessed via back button
        document.body.classList.add('no-history-nav');
        
        // Clear history state
        window.history.pushState(null, document.title, window.location.href);
        
        // Prevent back button navigation
        window.addEventListener('popstate', function() {
            window.history.pushState(null, document.title, window.location.href);
        });
        
        // Modify cache control headers via meta tags
        const metaNoCache = document.createElement('meta');
        metaNoCache.setAttribute('http-equiv', 'Cache-Control');
        metaNoCache.setAttribute('content', 'no-cache, no-store, must-revalidate');
        document.head.appendChild(metaNoCache);
        
        const metaNoStore = document.createElement('meta');
        metaNoStore.setAttribute('http-equiv', 'Pragma');
        metaNoStore.setAttribute('content', 'no-cache');
        document.head.appendChild(metaNoStore);
        
        const metaExpires = document.createElement('meta');
        metaExpires.setAttribute('http-equiv', 'Expires');
        metaExpires.setAttribute('content', '0');
        document.head.appendChild(metaExpires);
    }
}

/**
 * Setup automatic session timeout for security
 */
function setupSessionTimeout() {
    // Only apply to authenticated pages (not login page)
    if (window.location.href.includes('login')) return;

    let inactivityTime = 0;
    const maxInactivityTime = 30 * 60; // 30 minutes in seconds
    const warningTime = 25 * 60; // 25 minutes in seconds
    let warningDisplayed = false;
    
    // Reset the inactivity timer on user interaction
    function resetTimer() {
        inactivityTime = 0;
        
        // Hide warning if it was displayed
        if (warningDisplayed) {
            const warning = document.getElementById('session-warning');
            if (warning) {
                warning.parentNode.removeChild(warning);
            }
            warningDisplayed = false;
        }
    }
    
    // Display a warning before timeout
    function showWarning() {
        if (!warningDisplayed) {
            const warning = document.createElement('div');
            warning.id = 'session-warning';
            warning.style.cssText = 'position: fixed; top: 20px; right: 20px; background-color: #f44336; color: white; padding: 15px; border-radius: 4px; z-index: 9999; box-shadow: 0 2px 10px rgba(0,0,0,0.2);';
            warning.innerHTML = '<strong>Session Timeout Warning</strong><p>Your session will expire in 5 minutes due to inactivity. Please save your work.</p><button class="selector-button" style="background-color: white; color: #333; margin-top: 10px;">Continue Session</button>';
            document.body.appendChild(warning);
            
            warning.querySelector('button').addEventListener('click', resetTimer);
            warningDisplayed = true;
        }
    }
    
    // Check inactivity every second
    setInterval(function() {
        inactivityTime++;
        
        if (inactivityTime >= maxInactivityTime) {
            // Redirect to logout page when session times out
            window.location.href = '/admin/logout/';
        } else if (inactivityTime >= warningTime && !warningDisplayed) {
            showWarning();
        }
    }, 1000);
    
    // Reset timer on user activity
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(function(event) {
        document.addEventListener(event, resetTimer, true);
    });
}

/**
 * Setup blockchain visualizations on relevant pages
 */
function setupBlockchainVisualizations() {
    // Check if we're on a blockchain related page
    if (window.location.href.includes('blockchain') || window.location.href.includes('vote') || window.location.href.includes('election')) {
        // Add blockchain visualization elements if they don't exist
        const blockchainContainers = document.querySelectorAll('.blockchain-container');
        if (blockchainContainers.length === 0) return;
        
        // Simple visualization for each blockchain container
        blockchainContainers.forEach(function(container) {
            const blockIds = JSON.parse(container.dataset.blocks || '[]');
            if (!blockIds.length) return;
            
            const visualization = document.createElement('div');
            visualization.className = 'blockchain-visualization';
            visualization.style.cssText = 'display: flex; flex-wrap: nowrap; overflow-x: auto; padding: 15px 0; margin: 20px 0;';
            
            // Create blocks
            blockIds.forEach(function(blockId, index) {
                const block = document.createElement('div');
                block.className = 'blockchain-block';
                block.style.cssText = 'min-width: 150px; height: 100px; background: linear-gradient(135deg, #3949ab, #283593); margin-right: 15px; border-radius: 8px; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 3px 8px rgba(0,0,0,0.15); position: relative;';
                
                // Block content
                block.innerHTML = `
                    <div style="font-size: 18px; font-weight: bold;">Block ${index + 1}</div>
                    <div style="font-size: 12px; opacity: 0.8;">${blockId.substring(0, 8)}...</div>
                `;
                
                // Add chain link if not the first block
                if (index > 0) {
                    const link = document.createElement('div');
                    link.style.cssText = 'position: absolute; left: -15px; top: 50%; transform: translateY(-50%); width: 15px; height: 2px; background-color: #fff; opacity: 0.6;';
                    block.appendChild(link);
                }
                
                visualization.appendChild(block);
            });
            
            container.appendChild(visualization);
        });
    }
}

/**
 * Enhance dashboard cards and stats with animations and interactivity
 */
function enhanceDashboardElements() {
    // Add hover effects and animations to stats boxes
    document.querySelectorAll('.stats-box').forEach(function(box) {
        box.addEventListener('mouseover', function() {
            this.style.transform = 'translateY(-8px)';
        });
        
        box.addEventListener('mouseout', function() {
            this.style.transform = '';
        });
    });
    
    // Add click handlers to cards that should be clickable
    document.querySelectorAll('.card[data-url]').forEach(function(card) {
        card.style.cursor = 'pointer';
        
        card.addEventListener('click', function() {
            window.location.href = this.dataset.url;
        });
    });
}
