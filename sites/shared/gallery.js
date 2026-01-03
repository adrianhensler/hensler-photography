/**
 * Shared Gallery Application
 * Used by both adrian.hensler.photography and liam.hensler.photography
 *
 * DEPENDENCIES:
 * - Requires GLightbox library to be loaded
 * - Requires window.GALLERY_CONFIG = { userId: 1, siteName: 'Adrian Hensler' }
 * - Requires HTML elements: #slideshow, #gallery-grid, #category-pills, #tag-pills, #active-filters
 * - Optional HTML element: #featured-toggle (button group for featured vs all)
 */

(function(window) {
  'use strict';

  // ===== CONFIGURATION =====
  let config = window.GALLERY_CONFIG || { userId: 1, siteName: 'Site' };

  // ===== STATE VARIABLES =====
  let galleryImages = [];
  let galleryData = [];
  let galleryLightbox = null;
  let lightboxOpenTime = null;
  let currentLightboxImageId = null;
  const heroImpressions = new Set();

  // Slideshow state
  let currentSlide = 0;
  let slideshowInterval;
  let slideshowPaused = false;

  // Filtering state (shared with GalleryFilter module below)
  let allCategories = {};
  let allTags = {};
  let activeCategory = null;
  let activeTags = [];
  let featuredOnly = true;

  // ===== SLIDESHOW LOGIC =====

  function initSlideshow() {
    const container = document.getElementById('slideshow');
    if (!container) {
      console.warn('Slideshow container not found');
      return;
    }

    // The hero slideshow always uses the full published dataset,
    // independent of the featured-only gallery filter.
    const featuredImages = galleryData.filter(img => img.featured);

    // Weighted random: 70% featured, 30% any published
    let randomStart;
    if (featuredImages.length > 0 && Math.random() < 0.7) {
      // Pick from featured images (70% chance)
      const featuredIndex = Math.floor(Math.random() * featuredImages.length);
      randomStart = galleryData.indexOf(featuredImages[featuredIndex]);
    } else {
      // Pick from all images (30% chance)
      randomStart = Math.floor(Math.random() * galleryData.length);
    }

    currentSlide = randomStart;

    galleryData.forEach((imageData, index) => {
      const slide = document.createElement('div');
      slide.className = 'slideshow-slide';
      if (index === randomStart) slide.classList.add('active');

      const img = document.createElement('img');
      // Use large variant (1200px) for hero slideshow with responsive srcset
      img.src = imageData.large_url || imageData.medium_url || `/assets/gallery/${imageData.filename}`;
      img.srcset = `${imageData.medium_url} 800w, ${imageData.large_url} 1200w`;
      img.sizes = '100vw';
      img.alt = imageData.alt_text || imageData.title || `Photography by ${config.siteName}`;
      // Eager load ONLY the random start image for optimal LCP
      img.loading = index === randomStart ? 'eager' : 'lazy';

      slide.appendChild(img);
      slide.style.cursor = 'pointer';
      slide.addEventListener('click', () => openSlideLightbox(index));
      container.appendChild(slide);
    });

    // Auto-advance slideshow every 5 seconds
    startSlideshow();

    // Track first hero impression immediately (with random start)
    recordHeroImpression(randomStart);

    // Pause on hover
    container.addEventListener('mouseenter', () => {
      slideshowPaused = true;
      clearInterval(slideshowInterval);
    });

    container.addEventListener('mouseleave', () => {
      slideshowPaused = false;
      startSlideshow();
    });
  }

  function startSlideshow() {
    if (slideshowPaused) return;
    slideshowInterval = setInterval(() => {
      changeSlide(1);
    }, 5000);
  }

  function changeSlide(direction) {
    const slides = document.querySelectorAll('.slideshow-slide');
    slides[currentSlide].classList.remove('active');

    currentSlide = (currentSlide + direction + slides.length) % slides.length;

    slides[currentSlide].classList.add('active');

    recordHeroImpression(currentSlide);

    // Reset timer on manual navigation
    if (slideshowInterval) {
      clearInterval(slideshowInterval);
      startSlideshow();
    }
  }

  function recordHeroImpression(index) {
    const imageId = galleryData[index]?.id;
    if (imageId && !heroImpressions.has(imageId)) {
      heroImpressions.add(imageId);
      trackEvent('image_impression', imageId, { surface: 'hero_slideshow' });
    }
  }

  function openSlideLightbox(index) {
    const imageId = galleryData[index]?.id || index;
    trackEvent('gallery_click', imageId, { surface: 'hero_slideshow' });

    if (galleryLightbox) {
      currentLightboxImageId = imageId;
      lightboxOpenTime = Date.now();
      trackEvent('lightbox_open', imageId);
      galleryLightbox.openAt(index);
    } else {
      const galleryItems = document.querySelectorAll('.gallery-item');
      if (galleryItems[index]) {
        galleryItems[index].click();
      }
    }
  }

  // ===== GALLERY GRID LOGIC =====

  function initGallery() {
    const grid = document.getElementById('gallery-grid');
    if (!grid) {
      console.warn('Gallery grid not found');
      return;
    }

    galleryData.forEach((imageData, index) => {
      const link = document.createElement('a');
      // Use 1200px WebP variant for lightbox (optimized, not full-res)
      link.href = imageData.large_url || `/assets/gallery/${imageData.filename}`;
      link.className = 'gallery-item glightbox';
      link.setAttribute('data-gallery', 'portfolio');

      // Add title and EXIF data if available
      if (imageData.title) {
        link.setAttribute('data-title', imageData.title);
      }

      // Build description with EXIF data if shared
      let description = '';
      if (imageData.caption) {
        description += `<p style="margin: 0 0 0.75rem 0; color: #1a1a1a; font-size: 0.95rem; line-height: 1.5;">${imageData.caption}</p>`;

        // AI disclosure indicator (subtle, only if caption is AI-generated)
        if (imageData.ai_disclosure && imageData.ai_disclosure.caption) {
          description += `<p style="margin: 0 0 0.75rem 0; font-size: 0.7rem; color: #999; font-style: italic; opacity: 0.7;">AI-generated description</p>`;
        }
      }

      if (imageData.share_exif && imageData.exif) {
        const exif = imageData.exif;
        const exifParts = [];

        if (exif.camera_make || exif.camera_model) {
          const camera = [exif.camera_make, exif.camera_model].filter(Boolean).join(' ');
          if (camera) exifParts.push(camera);
        }
        if (exif.lens) exifParts.push(exif.lens);
        if (exif.focal_length) exifParts.push(exif.focal_length);
        if (exif.aperture) exifParts.push(exif.aperture);
        if (exif.shutter_speed) exifParts.push(exif.shutter_speed);
        if (exif.iso) exifParts.push(`ISO ${exif.iso}`);

        if (exifParts.length > 0) {
          description += `<p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666; font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; letter-spacing: 0.02em;">${exifParts.join(' · ')}</p>`;
        }

        if (exif.location) {
          description += `<p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;">📍 ${exif.location}</p>`;
        }
      }

      if (description) {
        link.setAttribute('data-description', description);
      }

      const img = document.createElement('img');
      // Use optimized WebP variants with responsive srcset
      img.src = imageData.thumbnail_url || `/assets/gallery/${imageData.filename}`;
      img.srcset = `${imageData.thumbnail_url} 400w, ${imageData.medium_url} 800w`;
      img.sizes = '(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw';
      img.alt = imageData.alt_text || imageData.title || `Photography by ${config.siteName}`;
      img.loading = 'lazy';
      img.setAttribute('decoding', 'async');
      img.setAttribute('fetchpriority', 'low');

      img.onload = () => {
        link.classList.add('has-image');
      };

      link.appendChild(img);
      grid.appendChild(link);
    });

    // Initialize GLightbox after gallery is populated
    setTimeout(() => {
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
    }, 100);

    // Staggered reveal as items scroll into view
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!prefersReducedMotion) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible');
            io.unobserve(e.target);
          }
        });
      }, { rootMargin: '120px' });

      document.querySelectorAll('.gallery-item').forEach(el => io.observe(el));
    } else {
      // Immediately show all items for users who prefer reduced motion
      document.querySelectorAll('.gallery-item').forEach(el => {
        el.classList.add('is-visible');
      });
    }
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
      const payload = {
        event_type: eventType,
        session_id: getSessionId()
      };

      if (imageId !== null) {
        payload.image_id = imageId;
      }

      // Get referrer from document
      if (document.referrer) {
        payload.referrer = document.referrer;
      }

      // Add metadata (duration, scroll depth, surface, etc.)
      if (metadata) {
        payload.metadata = JSON.stringify(metadata);
      }

      await fetch('/api/track', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
    } catch (error) {
      // Silently fail - don't disrupt user experience
      console.debug('Analytics tracking failed:', error);
    }
  }

  // Track page view on load
  function trackPageView() {
    trackEvent('page_view');
  }

  // Add click tracking to gallery items
  function addGalleryTracking() {
    document.querySelectorAll('.gallery-item').forEach((item, index) => {
      item.addEventListener('click', () => {
        // Use actual database ID instead of index for accurate analytics
        const imageId = galleryData[index]?.id || index;
        trackEvent('gallery_click', imageId);
      });
    });
  }

  // Track lightbox opens using GLightbox events
  function addLightboxTracking() {
    // Wait for GLightbox to be initialized
    setTimeout(() => {
      const lightboxElements = document.querySelectorAll('.glightbox');
      lightboxElements.forEach((element, index) => {
        element.addEventListener('click', () => {
          // Track when lightbox opens (not the gallery click, which was already tracked)
          setTimeout(() => {
            // Use actual database ID instead of index for accurate analytics
            const imageId = galleryData[index]?.id || index;
            trackEvent('lightbox_open', imageId);
            lightboxOpenTime = Date.now(); // Start duration tracking
          }, 100);
        });
      });

      // Track lightbox close and duration
      document.addEventListener('click', (e) => {
        if (e.target.classList.contains('gclose') || e.target.classList.contains('goverlay')) {
          if (lightboxOpenTime) {
            const duration = Math.round((Date.now() - lightboxOpenTime) / 1000); // seconds
            trackEvent('lightbox_close', null, { duration });
            lightboxOpenTime = null;
          }
        }
      });
    }, 200);
  }

  // Track image impressions (when images enter viewport)
  function addImpressionTracking() {
    const impressedImages = new Set(); // Prevent duplicate impressions

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          const index = parseInt(entry.target.dataset.index);
          const imageId = galleryData[index]?.id;

          if (imageId && !impressedImages.has(imageId)) {
            impressedImages.add(imageId);
            trackEvent('image_impression', imageId);
          }
        }
      });
    }, {
      threshold: 0.5, // 50% visible
      rootMargin: '0px'
    });

    // Observe all gallery items
    document.querySelectorAll('.gallery-item').forEach((item, index) => {
      item.dataset.index = index;
      observer.observe(item);
    });
  }

  // Track scroll depth milestones
  function addScrollDepthTracking() {
    const milestones = [25, 50, 75, 100];
    const reached = new Set();

    function checkScrollDepth() {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrollPercent = (scrollTop / docHeight) * 100;

      milestones.forEach(milestone => {
        if (scrollPercent >= milestone && !reached.has(milestone)) {
          reached.add(milestone);
          trackEvent('scroll_depth', null, { depth: milestone });
        }
      });
    }

    // Throttle scroll events
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
      window.galleryData = galleryData; // Export for filtering module

      // Extract filenames for backward compatibility
      galleryImages = galleryData.map(img => img.filename);

      console.log(`Loaded ${galleryData.length} published images from API for ${config.siteName}`);

      // Dynamically update preload hint with first featured image
      updatePreloadLink();

      return true;
    } catch (error) {
      console.error('Error loading gallery data:', error);
      // Fallback to empty gallery on error
      galleryImages = [];
      galleryData = [];
      window.galleryData = [];
      return false;
    }
  }

  // Update preload link dynamically for optimal LCP
  function updatePreloadLink() {
    if (galleryData.length === 0) return;

    const featuredImages = galleryData.filter(img => img.featured);
    const preloadImage = featuredImages.length > 0
      ? featuredImages[0].large_url
      : galleryData[0].large_url;

    // Update or create preload link
    let preloadLink = document.querySelector('link[rel="preload"][as="image"]');
    if (!preloadLink) {
      preloadLink = document.createElement('link');
      preloadLink.rel = 'preload';
      preloadLink.as = 'image';
      document.head.appendChild(preloadLink);
    }
    preloadLink.href = preloadImage;

    console.log('Preload link updated:', preloadImage);
  }

  // ===== GALLERY FILTERING MODULE =====
  // (Keep existing filtering logic from original shared/gallery.js)

  function aggregateFilters() {
    allCategories = {};
    allTags = {};

    if (!window.galleryData || window.galleryData.length === 0) {
      console.warn('No galleryData available for filtering');
      return;
    }

    window.galleryData.forEach(img => {
      // Aggregate categories
      if (img.category) {
        allCategories[img.category] = (allCategories[img.category] || 0) + 1;
      }

      // Aggregate tags (comma-separated string)
      if (img.tags) {
        img.tags.split(',').forEach(tag => {
          tag = tag.trim();
          if (tag) {
            allTags[tag] = (allTags[tag] || 0) + 1;
          }
        });
      }
    });

    console.log('Aggregated categories:', allCategories);
    console.log('Aggregated tags:', allTags);
  }

  function renderFilterSection() {
    // Render categories
    const categoryContainer = document.getElementById('category-pills');
    if (!categoryContainer) {
      console.error('Category pills container not found');
      return;
    }
    categoryContainer.innerHTML = '';

    Object.entries(allCategories)
      .sort((a, b) => b[1] - a[1]) // Sort by count descending
      .forEach(([category, count]) => {
        const pill = document.createElement('span');
        pill.className = 'pill';
        pill.dataset.category = category;
        pill.innerHTML = `${category} <span class="count">(${count})</span>`;
        pill.addEventListener('click', () => filterByCategory(category));
        categoryContainer.appendChild(pill);
      });

    // Render tags
    const tagContainer = document.getElementById('tag-pills');
    if (!tagContainer) {
      console.error('Tag pills container not found');
      return;
    }
    tagContainer.innerHTML = '';

    Object.entries(allTags)
      .sort((a, b) => b[1] - a[1]) // Sort by count descending
      .forEach(([tag, count]) => {
        const pill = document.createElement('span');
        pill.className = 'pill';
        pill.dataset.tag = tag;
        pill.innerHTML = `${tag} <span class="count">(${count})</span>`;
        pill.addEventListener('click', () => filterByTag(tag));
        tagContainer.appendChild(pill);
      });

    console.log('Filter section rendered');
  }

  function filterByCategory(category) {
    if (activeCategory === category) {
      // Deactivate if clicking same category
      activeCategory = null;
    } else {
      activeCategory = category;
    }
    applyFilters();
  }

  function filterByTag(tag) {
    const index = activeTags.indexOf(tag);
    if (index > -1) {
      // Remove tag if already active
      activeTags.splice(index, 1);
    } else {
      // Add tag
      activeTags.push(tag);
    }
    applyFilters();
  }

  function applyFilters() {
    // Filter galleryData
    let filteredData = window.galleryData;

    if (featuredOnly) {
      filteredData = filteredData.filter(img => img.featured);
    }

    if (activeCategory) {
      filteredData = filteredData.filter(img => img.category === activeCategory);
    }

    if (activeTags.length > 0) {
      filteredData = filteredData.filter(img => {
        if (!img.tags) return false;
        const imageTags = img.tags.split(',').map(t => t.trim());
        // Image must have ALL active tags (AND logic)
        return activeTags.every(activeTag => imageTags.includes(activeTag));
      });
    }

    console.log(`Filtered: ${filteredData.length} of ${window.galleryData.length} images`);

    // Update UI
    updateFilterUI();
    rerenderGallery(filteredData);

    // Update URL (optional)
    updateURL();
  }

  function updateFilterUI() {
    // Update active pills
    document.querySelectorAll('.pill').forEach(pill => {
      pill.classList.remove('active');
    });

    document.querySelector(`.pill[data-featured="${featuredOnly}"]`)?.classList.add('active');

    if (activeCategory) {
      document.querySelector(`.pill[data-category="${activeCategory}"]`)?.classList.add('active');
    }

    activeTags.forEach(tag => {
      document.querySelector(`.pill[data-tag="${tag}"]`)?.classList.add('active');
    });

    // Show/hide active filters section
    const activeFiltersDiv = document.getElementById('active-filters');
    const activeFilterText = document.getElementById('active-filter-text');

    if (activeFiltersDiv && activeFilterText) {
      if (featuredOnly || activeCategory || activeTags.length > 0) {
        activeFiltersDiv.style.display = 'flex';

        const parts = [];
        if (featuredOnly) parts.push('featured only');
        if (activeCategory) parts.push(`category: ${activeCategory}`);
      if (activeTags.length > 0) parts.push(`tags: ${activeTags.join(', ')}`);
      activeFilterText.textContent = parts.join('  •  ');
    } else {
        activeFiltersDiv.style.display = 'none';
      }
    }
  }

  function clearFilters() {
    activeCategory = null;
    activeTags = [];
    applyFilters();
  }

  function rerenderGallery(filteredData) {
    const grid = document.getElementById('gallery-grid');
    if (!grid) {
      console.error('Gallery grid not found');
      return;
    }

    grid.innerHTML = ''; // Clear existing

    if (filteredData.length === 0) {
      // Show "no results" message
      const noResults = document.createElement('div');
      noResults.className = 'gallery-placeholder';
      noResults.innerHTML = `
        <p style="font-size: 18px; opacity: 0.7;">no images match your filters</p>
        <button onclick="GalleryApp.GalleryFilter.clearFilters()">clear all filters</button>
      `;
      grid.appendChild(noResults);
      return;
    }

    // Re-render gallery items with category/tags in lightbox description
    filteredData.forEach((imageData, index) => {
      const link = document.createElement('a');
      link.href = `/assets/gallery/${imageData.filename}`;
      link.className = 'gallery-item glightbox';
      link.setAttribute('data-gallery', 'portfolio');

      if (imageData.title) {
        link.setAttribute('data-title', imageData.title);
      }

      // Build description with caption and EXIF
      let description = '';
      if (imageData.caption) {
        description += `<p style="margin: 0 0 0.75rem 0; color: #1a1a1a; font-size: 0.95rem; line-height: 1.5;">${imageData.caption}</p>`;

        // AI disclosure indicator (subtle, only if caption is AI-generated)
        if (imageData.ai_disclosure && imageData.ai_disclosure.caption) {
          description += `<p style="margin: 0 0 0.75rem 0; font-size: 0.7rem; color: #999; font-style: italic; opacity: 0.7;">AI-generated description</p>`;
        }
      }

      if (imageData.share_exif && imageData.exif) {
        const exif = imageData.exif;
        const exifParts = [];

        if (exif.camera_make || exif.camera_model) {
          const camera = [exif.camera_make, exif.camera_model].filter(Boolean).join(' ');
          if (camera) exifParts.push(camera);
        }
        if (exif.lens) exifParts.push(exif.lens);
        if (exif.focal_length) exifParts.push(exif.focal_length);
        if (exif.aperture) exifParts.push(exif.aperture);
        if (exif.shutter_speed) exifParts.push(exif.shutter_speed);
        if (exif.iso) exifParts.push(`ISO ${exif.iso}`);

        if (exifParts.length > 0) {
          description += `<p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666; font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; letter-spacing: 0.02em;">${exifParts.join(' · ')}</p>`;
        }

        if (exif.location) {
          description += `<p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;">📍 ${exif.location}</p>`;
        }
      }

      // ADD CATEGORY/TAGS TO LIGHTBOX DESCRIPTION
      description += '<div class="lightbox-pills">';

      if (imageData.category) {
        description += `<span class="lightbox-pill" onclick="GalleryApp.GalleryFilter.filterFromLightbox('category', '${imageData.category}')">${imageData.category}</span>`;
      }

      if (imageData.tags) {
        imageData.tags.split(',').forEach(tag => {
          tag = tag.trim();
          if (tag) {
            description += `<span class="lightbox-pill" onclick="GalleryApp.GalleryFilter.filterFromLightbox('tag', '${tag}')">${tag}</span>`;
          }
        });
      }

      description += '</div>';

      if (description) {
        link.setAttribute('data-description', description);
      }

      const img = document.createElement('img');
      img.src = `/assets/gallery/${imageData.filename}`;
      img.alt = imageData.alt_text || imageData.title || `Photography by ${config.siteName}`;
      img.loading = 'lazy';
      img.setAttribute('decoding', 'async');
      img.setAttribute('fetchpriority', 'low');

      img.onload = () => {
        link.classList.add('has-image');
        link.classList.add('is-visible'); // Show immediately (no stagger on rerender)
      };

      link.appendChild(img);
      grid.appendChild(link);
    });

    // Re-initialize GLightbox
    setTimeout(() => {
      if (window.GLightbox) {
        window.GLightbox({
          selector: '.glightbox',
          touchNavigation: true,
          loop: true,
          autoplayVideos: false,
          zoomable: false,
          draggable: true,
          closeButton: true,
          closeOnOutsideClick: true
        });
      }
    }, 100);
  }

  function updateURL() {
    const params = new URLSearchParams();

    if (activeCategory) {
      params.set('category', activeCategory);
    }

    if (activeTags.length > 0) {
      params.set('tags', activeTags.join(','));
    }

    const newURL = params.toString() ? `?${params.toString()}` : window.location.pathname;
    window.history.replaceState({}, '', newURL);
  }

  function loadFiltersFromURL() {
    const params = new URLSearchParams(window.location.search);

    if (params.has('category')) {
      activeCategory = params.get('category');
    }

    if (params.has('tags')) {
      activeTags = params.get('tags').split(',').map(t => t.trim()).filter(Boolean);
    }

    if (activeCategory || activeTags.length > 0) {
      applyFilters();
    }
  }

  function setFeaturedOnly(value) {
    featuredOnly = Boolean(value);
    applyFilters();
  }

  function filterFromLightbox(type, value) {
    // Close lightbox
    const closeBtn = document.querySelector('.gclose');
    if (closeBtn) closeBtn.click();

    // Apply filter after short delay (let lightbox close)
    setTimeout(() => {
      if (type === 'category') {
        filterByCategory(value);
      } else if (type === 'tag') {
        filterByTag(value);
      }

      // Scroll to gallery
      const galleryGrid = document.getElementById('gallery-grid');
      if (galleryGrid) {
        galleryGrid.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    }, 300);
  }

  function initFiltering() {
    console.log('Initializing gallery filters...');

    // Aggregate and render
    aggregateFilters();
    renderFilterSection();
    loadFiltersFromURL();

    const featuredToggle = document.getElementById('featured-toggle');
    if (featuredToggle) {
      featuredToggle.querySelectorAll('[data-featured]').forEach((button) => {
        button.addEventListener('click', () => {
          const value = button.dataset.featured === 'true';
          setFeaturedOnly(value);
        });
      });
    }

    applyFilters();

    // Setup clear filters button
    const clearBtn = document.getElementById('clear-filters');
    if (clearBtn) {
      clearBtn.addEventListener('click', clearFilters);
    }

    console.log('Gallery filters initialized');
  }

  // ===== MAIN INITIALIZATION =====

  async function init() {
    console.log('Initializing Gallery App for:', config.siteName);

    // Load gallery data from API first
    const loaded = await loadGalleryData();

    if (!loaded || galleryData.length === 0) {
      console.warn('No published images found');
      return;
    }

    // Initialize gallery UI
    initSlideshow();
    initGallery();

    // Initialize filtering
    initFiltering();

    // Initialize analytics tracking
    trackPageView();
    setTimeout(() => {
      addGalleryTracking();
      addLightboxTracking();
      addImpressionTracking();
      addScrollDepthTracking();
    }, 500); // Wait for gallery to be fully initialized

    console.log('Gallery App initialization complete');
  }

  // ===== PUBLIC API =====

  window.GalleryApp = {
    init: init,
    // Expose filtering API for backward compatibility
    GalleryFilter: {
      init: initFiltering,
      aggregateFilters: aggregateFilters,
      renderFilterSection: renderFilterSection,
      filterByCategory: filterByCategory,
      filterByTag: filterByTag,
      setFeaturedOnly: setFeaturedOnly,
      clearFilters: clearFilters,
      filterFromLightbox: filterFromLightbox,
      loadFiltersFromURL: loadFiltersFromURL
    }
  };

  // Also expose GalleryFilter at top level for backward compatibility
  window.GalleryFilter = window.GalleryApp.GalleryFilter;

})(window);
