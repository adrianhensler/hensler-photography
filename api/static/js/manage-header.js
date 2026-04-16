(function() {
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // Automatically attach X-CSRF-Token to all mutating fetch requests
    // so individual call sites don't need to be updated manually.
    function installCsrfInterceptor() {
        const MUTATING = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
        const origFetch = window.fetch;
        window.fetch = function(url, options) {
            options = options || {};
            const method = (options.method || 'GET').toUpperCase();
            if (MUTATING.has(method)) {
                const headers = new Headers(options.headers || {});
                if (!headers.has('X-CSRF-Token')) {
                    headers.set('X-CSRF-Token', getCsrfToken());
                }
                options = Object.assign({}, options, { headers });
            }
            return origFetch.call(this, url, options);
        };
    }


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
            const response = await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include'
            });
            if (!response.ok) {
                throw new Error(`Logout failed: ${response.status}`);
            }
            window.location.href = '/admin/login';
        } catch (error) {
            console.error('Logout error:', error);
            alert('Logout encountered an issue. Please clear your browser cache.');
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
        installCsrfInterceptor();
        initTheme();
        setupThemeToggle();
        setupDropdown();
        setupLogout();
    });

    // Expose for inline handlers if needed
    window.toggleTheme = toggleTheme;
    window.getCsrfToken = getCsrfToken;
})();
