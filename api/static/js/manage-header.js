(function() {
    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    function toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    }

    function setupThemeToggle() {
        const toggles = document.querySelectorAll('[data-theme-toggle]');
        toggles.forEach((toggle) => {
            toggle.addEventListener('click', toggleTheme);
        });
    }

    function closeDropdown(dropdown) {
        dropdown.classList.remove('active');
    }

    function setupDropdown() {
        const dropdown = document.querySelector('[data-user-dropdown]');
        const trigger = document.querySelector('[data-user-dropdown-trigger]');

        if (!dropdown || !trigger) {
            return;
        }

        trigger.addEventListener('click', (event) => {
            event.stopPropagation();
            dropdown.classList.toggle('active');
        });

        document.addEventListener('click', (event) => {
            if (!dropdown.contains(event.target)) {
                closeDropdown(dropdown);
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeDropdown(dropdown);
            }
        });
    }

    async function logout() {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            window.location.href = '/admin/login';
        }
    }

    function setupLogout() {
        const buttons = document.querySelectorAll('[data-logout-button]');
        buttons.forEach((button) => {
            button.addEventListener('click', logout);
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initTheme();
        setupThemeToggle();
        setupDropdown();
        setupLogout();
    });

    // Expose for inline handlers if needed
    window.toggleTheme = toggleTheme;
})();
