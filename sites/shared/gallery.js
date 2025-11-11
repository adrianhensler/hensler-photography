/**
 * Shared Gallery Filtering Logic
 * Used by both adrian.hensler.photography and liam.hensler.photography
 *
 * DEPENDENCIES:
 * - Requires galleryData global variable to be set by host page
 * - Requires GLightbox library to be loaded
 * - Requires HTML elements: #category-pills, #tag-pills, #active-filters, #gallery-grid
 */

(function(window) {
  'use strict';

  // ===== STATE =====
  let allCategories = {};
  let allTags = {};
  let activeCategory = null;
  let activeTags = [];

  // ===== AGGREGATION =====
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

  // ===== RENDERING =====
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

  // ===== FILTER ACTIONS =====
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
      if (activeCategory || activeTags.length > 0) {
        activeFiltersDiv.style.display = 'flex';

        const parts = [];
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
        <button onclick="GalleryFilter.clearFilters()">clear all filters</button>
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
        description += `<span class="lightbox-pill" onclick="GalleryFilter.filterFromLightbox('category', '${imageData.category}')">${imageData.category}</span>`;
      }

      if (imageData.tags) {
        imageData.tags.split(',').forEach(tag => {
          tag = tag.trim();
          if (tag) {
            description += `<span class="lightbox-pill" onclick="GalleryFilter.filterFromLightbox('tag', '${tag}')">${tag}</span>`;
          }
        });
      }

      description += '</div>';

      if (description) {
        link.setAttribute('data-description', description);
      }

      const img = document.createElement('img');
      img.src = `/assets/gallery/${imageData.filename}`;
      img.alt = imageData.title || 'Photography';
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

  // ===== URL STATE MANAGEMENT =====
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

  // ===== LIGHTBOX INTEGRATION =====
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

  // ===== INITIALIZATION =====
  function init() {
    console.log('Initializing gallery filters...');

    // Aggregate and render
    aggregateFilters();
    renderFilterSection();
    loadFiltersFromURL();

    // Setup clear filters button
    const clearBtn = document.getElementById('clear-filters');
    if (clearBtn) {
      clearBtn.addEventListener('click', clearFilters);
    }

    console.log('Gallery filters initialized');
  }

  // ===== PUBLIC API =====
  window.GalleryFilter = {
    init: init,
    aggregateFilters: aggregateFilters,
    renderFilterSection: renderFilterSection,
    filterByCategory: filterByCategory,
    filterByTag: filterByTag,
    clearFilters: clearFilters,
    filterFromLightbox: filterFromLightbox,
    loadFiltersFromURL: loadFiltersFromURL
  };

})(window);
