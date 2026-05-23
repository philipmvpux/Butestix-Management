// Get the API endpoint - works locally and on Vercel
function getApiEndpoint() {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:5000/api/signup';
    } else {
        // Vercel deployment
        return '/api/signup';
    }
}

// Smooth scroll to form
function scrollToForm() {
    const formSection = document.getElementById('form-section');
    if (formSection) {
        formSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// Form submission handler
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('accessForm');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const name = form.querySelector('input[type="text"]').value;
            const company = form.querySelectorAll('input[type="text"]')[1].value;
            const email = form.querySelector('input[type="email"]').value;
            
            // Basic validation
            if (!name.trim() || !company.trim() || !email.trim()) {
                alert('Bitte alle Felder ausfüllen');
                return;
            }
            
            // Prepare data
            const data = {
                name: name,
                company: company,
                email: email
            };
            
            // Send to server
            sendAccessRequest(data, form);
        });
    }
});

// Send access request to server
function sendAccessRequest(data, form) {
    const apiEndpoint = getApiEndpoint();
    
    fetch(apiEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            console.log('✅ Anfrage gespeichert');
            
            // Show success message
            form.style.display = 'none';
            const successMessage = document.getElementById('successMessage');
            if (successMessage) {
                successMessage.style.display = 'block';
            }
            
            // Reset form nach 5 Sekunden
            setTimeout(() => {
                form.reset();
                form.style.display = 'block';
                successMessage.style.display = 'none';
            }, 5000);
        } else {
            alert('Fehler beim Speichern. Bitte versuche es später nochmal.');
        }
    })
    .catch(error => {
        console.error('Fehler:', error);
        alert('Fehler beim Senden der Anfrage: ' + error);
    });
}

// Analytics - Track button clicks (optional)
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('btn-primary')) {
        console.log('Button clicked:', e.target.textContent);
    }
});

// Page load animation
document.addEventListener('DOMContentLoaded', function() {
    // Add slight animation on page load if desired
    document.body.style.opacity = '1';
});
