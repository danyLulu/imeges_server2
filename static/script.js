/**
 * --- ПОЛУЧЕНИЕ ЭЛЕМЕНТОВ ---
 */

document.addEventListener('DOMContentLoaded', () => {
    const heroPage = document.getElementById('hero-page');
    const mainAppPage = document.getElementById('main-app-page');
    const gotoAppButton = document.getElementById('goto-app-button');
    const navButtons = document.querySelectorAll('.app-nav__button');
    const uploadView = document.getElementById('upload-view');
    const imagesView = document.getElementById('images-view');
    const dropZone = document.getElementById('upload-drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const uploadError = document.getElementById('upload-error');
    const urlInput = document.getElementById('url-input');
    const copyBtn = document.getElementById('copy-btn');
    const imageList = document.getElementById('image-list');
    const imageItemTemplate = document.getElementById('image-item-template');

    const heroImages = [
        'assets/images/bird.png',
        'assets/images/cat.png',
        'assets/images/dog1.png',
        'assets/images/dog2.png',
        'assets/images/dog3.png',
    ];
    let uploadedImages = [];

    function setRandomHeroImage() {
        const randomIndex = Math.floor(Math.random() * heroImages.length);
        const randomImage = heroImages[randomIndex];
        
        // Добавляем анимацию смены фона
        heroPage.classList.add('background-changing');
        setTimeout(() => {
            heroPage.style.backgroundImage = `url(${randomImage})`;
            heroPage.classList.remove('background-changing');
        }, 400);
    }

    gotoAppButton.addEventListener(
        'click',
        () => {
            heroPage.classList.add('hidden');
            mainAppPage.classList.remove('hidden');
        }
    )

    // --- ЛОГИКА НАВИГАЦИИ ---
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const view = button.dataset.view;

            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            if (view === 'upload') {
                // Анимация перехода к загрузке
                imagesView.classList.add('hidden');
                setTimeout(() => {
                    uploadView.classList.remove('hidden');
                }, 150);
            } else {
                // Анимация перехода к списку изображений
                uploadView.classList.add('hidden');
                setTimeout(() => {
                    imagesView.classList.remove('hidden');
                    renderImages();
                }, 150);
            }
        })
    })

    function loadImagesFromLocalStorage() {
        const storedImages = localStorage.getItem('uploadedImages');
        if (storedImages) {
            try {
                uploadedImages = JSON.parse(storedImages);
                renderImages();
            } catch (e) {
                console.error("Ошибка при парсинге 'uploadedImages' из localStorage:", e);
                uploadedImages = [];
            }}}

        function saveImagesToLocalStorage() {
    localStorage.setItem('uploadedImages', JSON.stringify(uploadedImages));
    }

        // --- ЛОГИКА UPLOAD ---
        function handleFileUpload(file) {
            urlInput.value = '';
            uploadError.classList.add('hidden');
            
            // Добавляем анимацию загрузки
            browseBtn.classList.add('loading');
            browseBtn.disabled = true;
            browseBtn.textContent = 'Uploading...';

            const formData = new FormData();
            formData.append('file', file);

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    urlInput.value = data.url;
                    uploadedImages.push({ id: Date.now(), name: file.name, url: data.url });
                    saveImagesToLocalStorage();
                    
                    // Анимация успеха
                    browseBtn.classList.add('success-animation');
                    setTimeout(() => {
                        browseBtn.classList.remove('success-animation');
                    }, 600);
                    
                    if (imagesView.classList.contains('hidden')) {
                    } else {
                        renderImages();
                    }
                } else {
                    uploadError.textContent = data.message;
                    uploadError.classList.remove('hidden');
                    uploadError.classList.add('show');
                    setTimeout(() => {
                        uploadError.classList.remove('show');
                    }, 500);
                }
            })
            .catch(error => {
                console.error('Upload failed:', error);
                uploadError.textContent = 'Upload failed due to network error.';
                uploadError.classList.remove('hidden');
                uploadError.classList.add('show');
                setTimeout(() => {
                    uploadError.classList.remove('show');
                }, 500);
            })
            .finally(() => {
                // Убираем анимацию загрузки
                browseBtn.classList.remove('loading');
                browseBtn.disabled = false;
                browseBtn.textContent = 'Browse your file';
            });
        }

        browseBtn.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) handleFileUpload(fileInput.files[0]);
        });
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', (e) => {
            // Проверяем, что мы действительно покинули зону
            if (!dropZone.contains(e.relatedTarget)) {
                dropZone.classList.remove('dragover');
            }
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                // Анимация успешного drop
                dropZone.style.animation = 'successPulse 0.6s ease-out';
                setTimeout(() => {
                    dropZone.style.animation = '';
                }, 600);
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });
        copyBtn.addEventListener('click', () => {
            if (urlInput.value) {
                navigator.clipboard.writeText(urlInput.value).then(() => {
                    copyBtn.textContent = 'COPIED!';
                    copyBtn.classList.add('copied');
                    setTimeout(() => {
                        copyBtn.textContent = 'COPY';
                        copyBtn.classList.remove('copied');
                    }, 2000);
                }).catch(() => {
                    // Fallback для старых браузеров
                    urlInput.select();
                    document.execCommand('copy');
                    copyBtn.textContent = 'COPIED!';
                    copyBtn.classList.add('copied');
                    setTimeout(() => {
                        copyBtn.textContent = 'COPY';
                        copyBtn.classList.remove('copied');
                    }, 2000);
                });
            }
        });

        function renderImages() {
            imageList.innerHTML = '';
            if (uploadedImages.length === 0) {
                imageList.innerHTML = '<p style="text-align:center; color: var(--text-muted); padding: 20px;">No images uploaded yet.</p>';
                return;
            }
            uploadedImages.forEach(image => {
                const templateClone = imageItemTemplate.content.cloneNode(true);
                templateClone.querySelector('.image-item').dataset.id = image.id;
                templateClone.querySelector('.image-item__name span').textContent = image.name;
                const urlLink = templateClone.querySelector('.image-item__url a');
                urlLink.href = image.url;
                urlLink.textContent = image.url;
                imageList.appendChild(templateClone);
            });
        }

        imageList.addEventListener('click', (e) => {
            const deleteButton = e.target.closest('.delete-btn');
            if (deleteButton) {
                const listItem = e.target.closest('.image-item');
                const imageId = parseInt(listItem.dataset.id, 10);
                
                // Анимация удаления
                listItem.style.animation = 'slideInFromRight 0.3s ease-in-out reverse';
                setTimeout(() => {
                    uploadedImages = uploadedImages.filter(img => img.id !== imageId);
                    saveImagesToLocalStorage();
                    renderImages();
                }, 300);
            }
        });
        loadImagesFromLocalStorage();
        setRandomHeroImage();
    })
