# TODO - Future Improvements

## High Priority

### Password Reset Implementation
See `PASSWORD_RESET.md` for complete implementation guide.

**Status**: Documented, not implemented
**Priority**: HIGH before onboarding non-family photographers
**Effort**: 2-3 weeks
**Cost**: $0 (SendGrid free tier: 100 emails/day)

**Current Workaround**: CLI-based admin password reset
```bash
docker compose exec api python -m api.cli_utils set-password username "NewPassword123!"
```

---

## Medium Priority

### Accessibility Improvements

**Audit and improve accessibility across all sites:**

1. **Image Alt Text**
   - Add descriptive alt text to all gallery images
   - Add alt text to hero/slideshow images
   - Consider empty alt="" for decorative images (CSS backgrounds)
   - Tool: axe DevTools or Lighthouse accessibility audit

2. **Keyboard Navigation**
   - Ensure all interactive elements are keyboard accessible
   - Add visible focus indicators
   - Test tab order makes logical sense
   - Test Escape key closes modals/lightboxes

3. **Screen Reader Support**
   - Add proper ARIA labels where needed
   - Test with screen readers (NVDA, JAWS, VoiceOver)
   - Ensure image metadata is accessible
   - Add skip-to-content links

4. **Color Contrast**
   - Verify all text meets WCAG AA standards (4.5:1 ratio)
   - Dark mode already has good contrast
   - Check light mode contrast (if implemented)
   - Tool: Chrome DevTools contrast checker

5. **Semantic HTML**
   - Review and improve heading hierarchy (h1, h2, h3)
   - Use semantic elements (<nav>, <main>, <article>)
   - Add landmarks for screen reader navigation

6. **Form Accessibility**
   - Associate labels with inputs properly
   - Add error messages that screen readers can announce
   - Provide clear instructions for password requirements

**Testing Tools**:
- [axe DevTools](https://www.deque.com/axe/devtools/) (browser extension)
- Lighthouse (Chrome DevTools)
- [WAVE](https://wave.webaim.org/) (web accessibility evaluation tool)
- Screen reader testing (NVDA on Windows, VoiceOver on Mac)

**Target**: WCAG 2.1 Level AA compliance

---

## Low Priority

### Additional Features

- [ ] **Two-Factor Authentication (2FA)**: Add TOTP support for photographers
- [ ] **Social Sharing**: Add share buttons to individual images
- [ ] **Print Sales**: E-commerce integration for print orders
- [ ] **Advanced Search**: Filter gallery by category, camera, location
- [ ] **Image Collections**: Group images into albums/sets
- [ ] **Lightroom Integration**: Direct import from Lightroom catalog
- [ ] **CDN Integration**: CloudFlare Images or similar for better performance
- [ ] **Progressive Web App**: Offline support, install prompt
- [ ] **Analytics Dashboard**: More detailed metrics and reports

---

## Recently Completed

- ✅ Dark mode contrast fixes (edit button readable in dark theme)
- ✅ User dropdown with logout on all management pages
- ✅ Login page redesigned with blue theme
- ✅ Shared CSS architecture (`variables.css`, `admin-common.css`)
- ✅ WebP image variants for faster gallery loading
- ✅ Analytics system with impression tracking
- ✅ Main landing page redesign (hensler.photography)

---

**Last Updated**: 2025-11-20
