/**
 * Shared Gallery Application
 * Used by both adrian.hensler.photography and liam.hensler.photography
 *
 * Visitor-first design: a full-bleed hero slideshow, one category row,
 * and a justified grid that preserves aspect ratios. All curation
 * (featured flags, publishing) happens in the management console; the
 * only public control is the category filter, synced to ?category= in
 * the URL.
 *
 * DEPENDENCIES:
 * - GLightbox (self-hosted at /shared/vendor/glightbox/)
 * - window.GALLERY_CONFIG = { userId: 1, siteName: 'Adrian Hensler' }
 * - HTML elements: #slideshow, #gallery-grid; optional #category-nav
 */

(function(window) {
  'use strict';

  // ===== CONFIGURATION =====
  let config = window.GALLERY_CONFIG || { userId: 1, siteName: 'Site' };

  // A category earns a public pill only with enough images to feel like
  // a collection; everything below the threshold lives under "all"
  const MIN_CATEGORY_COUNT = 3;

  // ===== STATE =====
  let galleryData = [];        // full published dataset, API order
  let renderedData = [];       // subset currently rendered in the grid
  let activeCategory = null;   // null = all
  let galleryLightbox = null;
  let lightboxInitPromise = null;
  let lightboxOpenTime = null;

  // Slideshow state
  let slideshowData = [];
  let currentSlide = 0;
  let slideshowInterval;
  let slideshowPaused = false;
  const heroImpressions = new Set();

  // ===== SECURITY HELPERS =====

  /**
   * Escape HTML to prevent XSS attacks
   * @param {string} unsafe - Untrusted string that may contain HTML/script tags
   * @returns {string} - Safely escaped string for use in HTML context
   */
  function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') return '';
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ===== LIGHTBOX DESCRIPTION =====

  /**
   * Build lightbox description HTML with caption, AI disclosure, EXIF, and tags
   * @param {Object} imageData - Image data with caption, exif, ai_disclosure
   * @returns {string} - HTML string for GLightbox data-description attribute
   */
  function buildLightboxDescription(imageData) {
    let description = '';

    if (imageData.caption) {
      description += `<p style="margin: 0 0 0.75rem 0; color: #1a1a1a; font-size: 0.95rem; line-height: 1.5;">${escapeHtml(imageData.caption)}</p>`;
      if (imageData.ai_disclosure && imageData.ai_disclosure.caption) {
        description += `<p style="margin: 0 0 0.75rem 0; font-size: 0.7rem; color: #999; font-style: italic; opacity: 0.7;">AI-generated description</p>`;
      }
    }

    if (imageData.share_exif && imageData.exif) {
      const exif = imageData.exif;
      const exifParts = [];

      if (exif.camera_make || exif.camera_model) {
        const camera = [exif.camera_make, exif.camera_model].filter(Boolean).join(' ');
        if (camera) exifParts.push(escapeHtml(camera));
      }
      if (exif.lens) exifParts.push(escapeHtml(exif.lens));
      if (exif.focal_length) exifParts.push(escapeHtml(exif.focal_length));
      if (exif.aperture) exifParts.push(escapeHtml(exif.aperture));
      if (exif.shutter_speed) exifParts.push(escapeHtml(exif.shutter_speed));
      if (exif.iso) exifParts.push(`ISO ${escapeHtml(exif.iso)}`);

      if (exifParts.length > 0) {
        description += `<p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666; font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; letter-spacing: 0.02em;">${exifParts.join(' · ')}</p>`;
      }

      if (exif.location) {
        description += `<p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;">📍 ${escapeHtml(exif.location)}</p>`;
      }
    }

    // Category and tags as quiet metadata (display only, not controls)
    const metaParts = [];
    if (imageData.category) metaParts.push(escapeHtml(imageData.category));
    if (imageData.tags) {
      imageData.tags.split(',').slice(0, 5).forEach(tag => {
        tag = tag.trim();
        if (tag) metaParts.push(escapeHtml(tag));
      });
    }
    if (metaParts.length > 0) {
      description += `<p style="margin: 0.6rem 0 0 0; font-size: 0.78rem; color: #999; letter-spacing: 0.03em;">${metaParts.join(' · ')}</p>`;
    }

    return description;
  }

  // ===== GALLERY GRID =====

  /**
   * Create a gallery item <a> element sized for the justified grid
   * @param {Object} imageData - Image data object
   * @param {number} index - Index within the rendered dataset
   * @returns {HTMLElement} - <a> element ready to append to grid
   */
  function createGalleryItem(imageData, index) {
    const ratio = Number(imageData.aspect_ratio) ||
      (imageData.width && imageData.height ? imageData.width / imageData.height : 1.5);

    const link = document.createElement('a');
    link.href = imageData.large_url || `/assets/gallery/${imageData.filename}`;
    link.className = 'gallery-item glightbox';
    link.setAttribute('data-gallery', 'portfolio');
    link.dataset.index = index;

    // Justified rows: width share proportional to aspect ratio
    link.style.flexGrow = String(ratio * 100);
    link.style.flexBasis = `${Math.round(ratio * 240)}px`;
    link.style.aspectRatio = String(ratio);

    if (imageData.title) {
      link.setAttribute('data-title', imageData.title);
    }

    const description = buildLightboxDescription(imageData);
    if (description) {
      link.setAttribute('data-description', description);
    }

    const img = document.createElement('img');
    img.src = imageData.thumbnail_url || `/assets/gallery/${imageData.filename}`;
    if (imageData.thumbnail_url && imageData.medium_url) {
      img.srcset = `${imageData.thumbnail_url} 400w, ${imageData.medium_url} 800w`;
      img.sizes = '(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw';
    }
    img.alt = imageData.alt_text || imageData.title || `Photography by ${config.siteName}`;
    img.loading = 'lazy';
    img.setAttribute('decoding', 'async');

    img.onload = () => link.classList.add('has-image');

    link.appendChild(img);
    return link;
  }

  function renderGallery() {
    const grid = document.getElementById('gallery-grid');
    if (!grid) {
      console.warn('Gallery grid not found');
      return;
    }

    renderedData = activeCategory
      ? galleryData.filter(img => img.category === activeCategory)
      : galleryData;

    grid.innerHTML = '';
    const fragment = document.createDocumentFragment();
    renderedData.forEach((imageData, index) => {
      fragment.appendChild(createGalleryItem(imageData, index));
    });
    grid.appendChild(fragment);

    revealItems();
    reinitLightbox();
    addImpressionTracking();
  }

  function revealItems() {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const items = document.querySelectorAll('.gallery-item');

    if (prefersReducedMotion) {
      items.forEach(el => el.classList.add('is-visible'));
      return;
    }

    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('is-visible');
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: '120px' });

    items.forEach(el => io.observe(el));
  }

  // ===== LIGHTBOX =====

  function reinitLightbox() {
    if (galleryLightbox) {
      galleryLightbox.destroy();
      galleryLightbox = null;
    }
    lightboxInitPromise = null;
    ensureLightboxReady().catch((error) => {
      console.error('Failed to initialize lightbox:', error);
    });
  }

  function ensureLightboxReady() {
    if (galleryLightbox) {
      return Promise.resolve(galleryLightbox);
    }

    if (!lightboxInitPromise) {
      lightboxInitPromise = new Promise((resolve, reject) => {
        setTimeout(() => {
          if (!window.GLightbox) {
            reject(new Error('GLightbox not available'));
            return;
          }

          galleryLightbox = window.GLightbox({
            selector: '.glightbox',
            touchNavigation: true,
            loop: true,
            autoplayVideos: false,
            zoomable: false,
            draggable: true,
            closeButton: true,
            closeOnOutsideClick: true
          });
          resolve(galleryLightbox);
        }, 100);
      }).finally(() => {
        lightboxInitPromise = null;
      });
    }

    return lightboxInitPromise;
  }

  function openLightboxForImage(imageData) {
    // The lightbox holds the currently rendered items; if the image is
    // filtered out, clear the filter first so it can be shown
    let position = renderedData.indexOf(imageData);
    if (position === -1) {
      filterByCategory(null, { historyMode: 'replace' });
      position = renderedData.indexOf(imageData);
    }
    if (position === -1) return;

    const imageId = imageData.id;
    ensureLightboxReady()
      .then(() => {
        lightboxOpenTime = Date.now();
        trackEvent('lightbox_open', imageId);
        galleryLightbox.openAt(position);
      })
      .catch((error) => {
        console.error('Lightbox init failed:', error);
      });
  }

  // ===== SLIDESHOW =====

  function initSlideshow() {
    const container = document.getElementById('slideshow');
    if (!container) {
      console.warn('Slideshow container not found');
      return;
    }

    // The hero is curated: featured images when there are enough of them
    // to carry it, otherwise the full published set
    const featured = galleryData.filter(img => img.featured);
    slideshowData = featured.length >= MIN_CATEGORY_COUNT ? featured : galleryData;

    if (slideshowData.length === 0) {
      console.warn('No images available for slideshow');
      return;
    }

    // Deterministic first slide for a predictable, preloadable LCP
    currentSlide = 0;

    slideshowData.forEach((imageData, index) => {
      const slide = document.createElement('div');
      slide.className = 'slideshow-slide';
      if (index === 0) slide.classList.add('active');

      const img = document.createElement('img');
      img.src = imageData.large_url || imageData.medium_url || `/assets/gallery/${imageData.filename}`;
      if (imageData.medium_url && imageData.large_url) {
        img.srcset = `${imageData.medium_url} 800w, ${imageData.large_url} 1200w`;
        img.sizes = '100vw';
      }
      img.alt = imageData.alt_text || imageData.title || `Photography by ${config.siteName}`;
      img.loading = index === 0 ? 'eager' : 'lazy';
      if (index === 0) img.setAttribute('fetchpriority', 'high');

      slide.appendChild(img);
      slide.style.cursor = 'pointer';
      slide.addEventListener('click', () => {
        trackEvent('gallery_click', imageData.id, { surface: 'hero_slideshow' });
        openLightboxForImage(imageData);
      });
      container.appendChild(slide);
    });

    recordHeroImpression(0);
    startSlideshow();

    container.addEventListener('mouseenter', () => {
      slideshowPaused = true;
      clearInterval(slideshowInterval);
    });

    container.addEventListener('mouseleave', () => {
      slideshowPaused = false;
      startSlideshow();
    });

    const prevButton = document.querySelector('.slideshow-prev');
    const nextButton = document.querySelector('.slideshow-next');
    if (prevButton) prevButton.addEventListener('click', () => changeSlide(-1));
    if (nextButton) nextButton.addEventListener('click', () => changeSlide(1));
  }

  function startSlideshow() {
    if (slideshowPaused) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    // Guard against stacking multiple intervals
    clearInterval(slideshowInterval);
    slideshowInterval = setInterval(() => changeSlide(1), 5000);
  }

  function changeSlide(direction) {
    const slides = document.querySelectorAll('.slideshow-slide');
    if (slides.length === 0) return;

    slides[currentSlide].classList.remove('active');
    currentSlide = (currentSlide + direction + slides.length) % slides.length;
    slides[currentSlide].classList.add('active');

    recordHeroImpression(currentSlide);

    if (slideshowInterval) {
      clearInterval(slideshowInterval);
      startSlideshow();
    }
  }

  function recordHeroImpression(index) {
    const imageId = slideshowData[index]?.id;
    if (imageId && !heroImpressions.has(imageId)) {
      heroImpressions.add(imageId);
      trackEvent('image_impression', imageId, { surface: 'hero_slideshow' });
    }
  }

  // ===== CATEGORY FILTERING =====

  function getPublicCategories() {
    const counts = {};
    galleryData.forEach(img => {
      if (img.category) {
        counts[img.category] = (counts[img.category] || 0) + 1;
      }
    });
    return Object.entries(counts)
      .filter(([, count]) => count >= MIN_CATEGORY_COUNT)
      .sort((a, b) => b[1] - a[1])
      .map(([category]) => category);
  }

  function renderCategoryNav() {
    const nav = document.getElementById('category-nav');
    if (!nav) return;

    const categories = getPublicCategories();

    // A single category (or none) doesn't warrant navigation
    if (categories.length < 2) {
      nav.hidden = true;
      return;
    }

    nav.innerHTML = '';
    const makeButton = (label, category) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'category-link';
      button.textContent = label;
      const isActive = activeCategory === category;
      button.classList.toggle('active', isActive);
      button.setAttribute('aria-pressed', String(isActive));
      button.addEventListener('click', () => filterByCategory(category));
      return button;
    };

    nav.appendChild(makeButton('all', null));
    categories.forEach(category => nav.appendChild(makeButton(category, category)));
    nav.hidden = false;
  }

  function filterByCategory(category, options = {}) {
    const { historyMode = 'push' } = options;
    activeCategory = category || null;

    renderGallery();
    renderCategoryNav();
    updateURL({ mode: historyMode });
  }

  function buildFilterURL() {
    const params = new URLSearchParams();
    if (activeCategory) {
      params.set('category', activeCategory);
    }
    const queryString = params.toString();
    const basePath = window.location.pathname;
    const hash = window.location.hash || '';
    return queryString ? `${basePath}?${queryString}${hash}` : `${basePath}${hash}`;
  }

  function updateURL({ mode = 'push' } = {}) {
    const newURL = buildFilterURL();
    const currentURL = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (newURL === currentURL) return;

    if (mode === 'replace') {
      window.history.replaceState({}, '', newURL);
    } else {
      window.history.pushState({}, '', newURL);
    }
  }

  function loadFiltersFromURL() {
    const params = new URLSearchParams(window.location.search);
    activeCategory = null;

    // Validate against the public category list (XSS protection, and
    // sub-threshold categories fold into "all" rather than landing the
    // visitor on an orphan view with no matching nav item)
    if (params.has('category')) {
      const requested = params.get('category');
      if (getPublicCategories().includes(requested)) {
        activeCategory = requested;
      } else {
        console.warn('Invalid or non-public category from URL:', requested);
      }
    }

    renderGallery();
    renderCategoryNav();
  }

  // ===== ANALYTICS TRACKING =====

  // Session ID management (ephemeral, no PII)
  function getSessionId() {
    let sessionId = sessionStorage.getItem('analytics_session');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('analytics_session', sessionId);
    }
    return sessionId;
  }

  // Track events to analytics endpoint
  async function trackEvent(eventType, imageId = null, metadata = null) {
    try {
      // Check if user is authenticated by calling /api/users/me
      // session_token is httpOnly, so it can't be read from document.cookie;
      // the browser sends it automatically with credentials: 'include'
      let isPhotographer = false;

      try {
        const userResponse = await fetch('/api/users/me', {
          credentials: 'include'
        });

        if (userResponse.ok) {
          const user = await userResponse.json();
          if (!user.track_own_activity) {
            // Photographer opted out — don't track at all
            return;
          }
          isPhotographer = true;
        }
        // 401 → not authenticated → track as visitor
      } catch (e) {
        // Network error — fail gracefully and track as visitor
      }

      const payload = {
        event_type: eventType,
        session_id: getSessionId(),
        is_photographer: isPhotographer
      };

      if (imageId !== null) {
        payload.image_id = imageId;
      }

      if (document.referrer) {
        payload.referrer = document.referrer;
      }

      if (metadata) {
        payload.metadata = JSON.stringify(metadata);
      }

      await fetch('/api/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (error) {
      // Silently fail — never disrupt the visitor experience
    }
  }

  function trackPageView() {
    trackEvent('page_view');
  }

  // Delegated click + lightbox-open tracking for grid items (survives rerenders)
  function addGalleryTracking() {
    document.addEventListener('click', (e) => {
      const item = e.target.closest('.gallery-item');
      if (item) {
        const imageData = renderedData[Number(item.dataset.index)];
        if (imageData) {
          trackEvent('gallery_click', imageData.id);
          setTimeout(() => {
            trackEvent('lightbox_open', imageData.id);
            lightboxOpenTime = Date.now();
          }, 100);
        }
        return;
      }

      // Lightbox close → duration
      if (e.target.classList.contains('gclose') || e.target.classList.contains('goverlay')) {
        if (lightboxOpenTime) {
          const duration = Math.round((Date.now() - lightboxOpenTime) / 1000);
          trackEvent('lightbox_close', null, { duration });
          lightboxOpenTime = null;
        }
      }
    });
  }

  // Track image impressions (50% visible in viewport)
  const impressedImages = new Set();
  function addImpressionTracking() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          const imageData = renderedData[Number(entry.target.dataset.index)];
          if (imageData && !impressedImages.has(imageData.id)) {
            impressedImages.add(imageData.id);
            trackEvent('image_impression', imageData.id);
          }
        }
      });
    }, { threshold: 0.5 });

    document.querySelectorAll('.gallery-item').forEach(item => observer.observe(item));
  }

  // Track scroll depth milestones
  function addScrollDepthTracking() {
    const milestones = [25, 50, 75, 100];
    const reached = new Set();

    function checkScrollDepth() {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      if (docHeight <= 0) return;
      const scrollPercent = (scrollTop / docHeight) * 100;

      milestones.forEach(milestone => {
        if (scrollPercent >= milestone && !reached.has(milestone)) {
          reached.add(milestone);
          trackEvent('scroll_depth', null, { depth: milestone });
        }
      });
    }

    let scrollTimeout;
    window.addEventListener('scroll', () => {
      if (scrollTimeout) clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(checkScrollDepth, 200);
    });
  }

  // ===== LOAD GALLERY DATA FROM API =====

  async function loadGalleryData() {
    try {
      const response = await fetch(`/api/gallery/published?user_id=${config.userId}`);
      if (!response.ok) {
        throw new Error(`Failed to load gallery: ${response.status}`);
      }

      const data = await response.json();
      galleryData = data.images || [];
      window.galleryData = galleryData;
      return true;
    } catch (error) {
      console.error('Error loading gallery data:', error);
      galleryData = [];
      window.galleryData = [];
      return false;
    }
  }

  // ===== MAIN INITIALIZATION =====

  async function init() {
    const loaded = await loadGalleryData();

    if (!loaded || galleryData.length === 0) {
      console.warn('No published images found');
      return;
    }

    initSlideshow();
    loadFiltersFromURL();   // renders grid + category nav from URL state

    window.addEventListener('popstate', () => loadFiltersFromURL());

    trackPageView();
    addGalleryTracking();
    addScrollDepthTracking();
  }

  // ===== PUBLIC API =====

  window.GalleryApp = {
    init: init,
    Slideshow: {
      next: () => changeSlide(1),
      prev: () => changeSlide(-1),
      changeSlide: changeSlide
    },
    GalleryFilter: {
      filterByCategory: filterByCategory,
      clearFilters: () => filterByCategory(null),
      loadFiltersFromURL: loadFiltersFromURL
    }
  };

  // Backward compatibility
  window.GalleryFilter = window.GalleryApp.GalleryFilter;
})(window);
