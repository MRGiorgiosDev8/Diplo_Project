document.addEventListener("DOMContentLoaded", function() {
    let notification = document.getElementById('notification');

    function showNotification(sender) {
        notification.innerText = `Сообщение от ${sender}!!!`;
        notification.style.display = 'block';

        gsap.to(notification, { duration: 1, y: -50, ease: "power2.out" });

        setTimeout(function() {
            hideNotification();
        }, 7000);
    }

    // Скрываем уведомление
    function hideNotification() {
        gsap.to(notification, { duration: 0.5, y: 100, ease: "power2.in", onComplete: () => {
            notification.style.display = 'none';
        }});
    }

    function updateUnreadCountAndNotification() {
        fetch('/accounts/unread_message_count/')
            .then(response => response.json())
            .then(data => {
                let unreadCount = data.unread_count;
                let sender = data.sender || "Анонимный отправитель";
                if (unreadCount > 0) {
                    showNotification(sender);
                } else {
                    hideNotification();
                }
            })
            .catch(error => {
                console.error('Error fetching unread message count:', error);
            });
    }

    updateUnreadCountAndNotification();
});