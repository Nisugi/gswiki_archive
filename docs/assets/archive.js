/**
 * GSWiki Archive JavaScript
 * Handles image fallback and other archive functionality
 */

(function() {
    'use strict';

    /**
     * Handle image load errors by applying fallback styling
     */
    function handleImageError(img) {
        // Don't process twice
        if (img.classList.contains('archive-img-unavailable')) {
            return;
        }

        // Store original dimensions if available
        const width = img.getAttribute('width') || img.naturalWidth || 150;
        const height = img.getAttribute('height') || img.naturalHeight || 100;

        // Apply fallback class
        img.classList.add('archive-img-unavailable');

        // Preserve dimensions for layout
        img.style.width = width + 'px';
        img.style.height = height + 'px';

        // Clear the broken src to prevent repeated errors
        img.removeAttribute('src');
    }

    /**
     * Set up error handlers for all images on the page
     */
    function setupImageFallbacks() {
        // Handle images that are already in the DOM
        document.querySelectorAll('img').forEach(function(img) {
            // If image already failed to load
            if (img.complete && img.naturalHeight === 0) {
                handleImageError(img);
            }

            // Add error handler for future failures
            img.addEventListener('error', function() {
                handleImageError(this);
            });
        });

        // Handle dynamically added images
        var observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeName === 'IMG') {
                        node.addEventListener('error', function() {
                            handleImageError(this);
                        });
                    }
                    // Check for images inside added elements
                    if (node.querySelectorAll) {
                        node.querySelectorAll('img').forEach(function(img) {
                            img.addEventListener('error', function() {
                                handleImageError(this);
                            });
                        });
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Add keyboard shortcut to toggle banner visibility
     * (Useful for screenshots)
     */
    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Alt+B to toggle banner
            if (e.altKey && e.key === 'b') {
                var banner = document.getElementById('archive-banner');
                if (banner) {
                    banner.style.display = banner.style.display === 'none' ? '' : 'none';
                    document.body.style.paddingTop = banner.style.display === 'none' ? '0' : '';
                }
            }
        });
    }

    /**
     * Update the banner timestamp to show relative time
     */
    function updateRelativeTime() {
        var banner = document.querySelector('.archive-text');
        if (!banner) return;

        var match = banner.textContent.match(/Captured: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC/);
        if (!match) return;

        var crawlDate = new Date(match[1] + ' UTC');
        var now = new Date();
        var diffMs = now - crawlDate;
        var diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        var relativeText = '';
        if (diffDays === 0) {
            relativeText = ' (today)';
        } else if (diffDays === 1) {
            relativeText = ' (yesterday)';
        } else if (diffDays < 7) {
            relativeText = ' (' + diffDays + ' days ago)';
        } else if (diffDays < 30) {
            var weeks = Math.floor(diffDays / 7);
            relativeText = ' (' + weeks + ' week' + (weeks > 1 ? 's' : '') + ' ago)';
        } else {
            var months = Math.floor(diffDays / 30);
            relativeText = ' (' + months + ' month' + (months > 1 ? 's' : '') + ' ago)';
        }

        // Append relative time if not already there
        if (!banner.textContent.includes('ago)') && !banner.textContent.includes('today)') && !banner.textContent.includes('yesterday)')) {
            banner.innerHTML = banner.innerHTML.replace(
                /UTC/,
                'UTC<span class="archive-relative-time" style="color: #888;">' + relativeText + '</span>'
            );
        }
    }

    /**
     * Initialize all archive functionality
     */
    function init() {
        setupImageFallbacks();
        setupKeyboardShortcuts();
        updateRelativeTime();

        console.log('GSWiki Archive: Initialized');
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
