document.addEventListener('DOMContentLoaded', function () {

    // Progress bar otomatis berjalan
    let progress = document.getElementById('story-progress');
    let width = 0;
    let timer = setInterval(() => {
        width++;
        progress.style.width = width + "%";
        if (width >= 100) {
            clearInterval(timer);
            window.location.href = exitUrl; // variabel exitUrl bisa di-setup di template
        }
    }, 100);

    // Swipe gesture handling (mobile support)
    let startX = 0;
    let storyContainer = document.querySelector('.story-fullscreen');

    storyContainer.addEventListener('touchstart', function (e) {
        startX = e.changedTouches[0].screenX;
    }, false);

    storyContainer.addEventListener('touchend', function (e) {
        let endX = e.changedTouches[0].screenX;
        handleSwipe(startX, endX);
    }, false);

    function handleSwipe(start, end) {
        let diff = start - end;
        if (diff > 100) {
            // Swipe ke kiri (next story)
            goNextStory();
        } else if (diff < -100) {
            // Swipe ke kanan (prev story)
            goPrevStory();
        }
    }

    function goNextStory() {
        // Bisa kita isi nextUrl jika multi story
        // Untuk sekarang kita close saja
        clearInterval(timer);
        window.location.href = exitUrl;
    }

    function goPrevStory() {
        // Kalau mau previous story nanti bisa kita tambah
        clearInterval(timer);
        window.location.href = exitUrl;
    }

});
