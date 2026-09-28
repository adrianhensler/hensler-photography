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


    // Theme: an explicit choice (saved by the toggle) wins; otherwise the
    // console follows the OS setting, live, as sites/main/design.html specifies.
    const osDark = window.matchMedia('(prefers-color-scheme: dark)');
    const osTheme = () => (osDark.matches ? 'dark' : 'light');

    function savedTheme() {
        try {
            const theme = localStorage.getItem('theme');
            return theme === 'dark' || theme === 'light' ? theme : null;
        } catch (e) {
            return null;
        }
    }

    // Pages that paint with resolved token values (e.g. the analytics
    // chart) listen for 'themechange' to repaint.
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    }

    function initTheme() {
        document.documentElement.setAttribute('data-theme', savedTheme() || osTheme());
        osDark.addEventListener('change', () => {
            if (!savedTheme()) applyTheme(osTheme());
        });
    }

    function toggleTheme() {
        const html = document.documentElement;
        const newTheme = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        try {
            // Toggling back to the OS theme clears the override, so the
            // console resumes following the OS.
            if (newTheme === osTheme()) localStorage.removeItem('theme');
            else localStorage.setItem('theme', newTheme);
        } catch (e) { /* storage blocked: choice lasts for this page only */ }
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
