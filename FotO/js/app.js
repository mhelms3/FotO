document.addEventListener('DOMContentLoaded', async () => {
    const contentArea = document.getElementById('content-area');
    const indexContainer = document.getElementById('episode-index-container');

    // 1. Load the Episode Index dynamically into the sidebar
    await loadEpisodeIndex();

    // 2. Fetch and render requested episode page
    async function loadEpisode(fileSrc) {
        try {
            const response = await fetch(fileSrc);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const html = await response.text();
            contentArea.innerHTML = html;
            
            initCollapsibles();
            initAudioPlaylist();
            initImageGallery();
            
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (error) {
            contentArea.innerHTML = `<p style="color: red;">Error loading episode content (${fileSrc}). Make sure you are using a local server (e.g. VS Code Live Server).</p>`;
            console.error('Failed to load episode:', error);
        }
    }

    // 3. Fetch episodeindex.html and bind buttons
    async function loadEpisodeIndex() {
        if (!indexContainer) return;
        
        try {
            const response = await fetch('episodes/episodeindex.html');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const indexHtml = await response.text();
            indexContainer.innerHTML = indexHtml;
            
            bindEpisodeButtons();
        } catch (error) {
            indexContainer.innerHTML = `<p style="color: red; font-size: 0.8rem;">Error loading index menu.</p>`;
            console.error('Failed to load episode index:', error);
        }
    }

    // 4. Attach click handlers to dynamically created episode buttons
    function bindEpisodeButtons() {
        const epButtons = indexContainer.querySelectorAll('.ep-btn');

        epButtons.forEach(button => {
            button.addEventListener('click', () => {
                epButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                const fileSrc = button.getAttribute('data-src');
                if (fileSrc) loadEpisode(fileSrc);
            });
        });

        // Automatically activate and load the first episode in the list
        if (epButtons.length > 0) {
            epButtons[0].classList.add('active');
            loadEpisode(epButtons[0].getAttribute('data-src'));
        }
    }

    // --- PLAYLIST LOGIC ---
    function initAudioPlaylist() {
        const player = document.getElementById('main-audio-player');
        const audioSource = document.getElementById('audio-source');
        const nowPlaying = document.getElementById('now-playing');
        const trackButtons = document.querySelectorAll('.track-btn');

        if (!player || trackButtons.length === 0) return;

        trackButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const newSrc = this.getAttribute('data-src');
                const trackName = this.innerText;

                trackButtons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                audioSource.src = newSrc;
                player.load();
                player.play();

                nowPlaying.innerText = `Now Playing: ${trackName}`;
            });
        });
    }

    // --- GALLERY LIGHTBOX LOGIC ---
    function initImageGallery() {
        const lightbox = document.getElementById('lightbox');
        const lightboxImg = document.getElementById('lightbox-img');
        const lightboxCaption = document.getElementById('lightbox-caption');
        const closeBtn = document.querySelector('.lightbox-close');
        const galleryItems = document.querySelectorAll('.gallery-item');

        if (!lightbox) return;

        galleryItems.forEach(item => {
            item.addEventListener('click', () => {
                const img = item.querySelector('img');
                const caption = item.querySelector('.caption');
                
                lightbox.style.display = "block";
                lightboxImg.src = img.src;
                lightboxCaption.innerText = caption ? caption.innerText : '';
            });
        });

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                lightbox.style.display = "none";
            });
        }

        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) {
                lightbox.style.display = "none";
            }
        });
    }

    // --- COLLAPSIBLE SECTIONS ---
    function initCollapsibles() {
        const collapsibles = contentArea.querySelectorAll('.collapsible-btn');
        collapsibles.forEach(btn => {
            btn.addEventListener('click', function() {
                this.classList.toggle('active');
                const icon = this.querySelector('.icon');
                if (icon) icon.textContent = icon.textContent === '+' ? '−' : '+';

                const content = this.nextElementSibling;
                if (content.style.maxHeight) {
                    content.style.maxHeight = null;
                } else {
                    content.style.maxHeight = content.scrollHeight + "px";
                }
            });
        });
    }
});