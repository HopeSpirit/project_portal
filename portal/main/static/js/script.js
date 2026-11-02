document.querySelectorAll('.background-logos img').forEach(img => {
const x = Math.random() * 90;  // 0-90%
const y = Math.random() * 90;  // 0-90%
img.style.left = x + '%';
img.style.top = y + '%';
// img.style.transform = `rotate(${Math.random() * 360}deg)`; // случайный поворот
});