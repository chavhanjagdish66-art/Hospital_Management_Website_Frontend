/* =========================================================
   PATIL HOSPITAL - JAVASCRIPT
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       PASSWORD SHOW / HIDE
    ===================================================== */

    window.togglePassword = function () {

        const password =
            document.getElementById("password");

        if (!password) {
            return;
        }

        if (password.type === "password") {

            password.type = "text";

        } else {

            password.type = "password";

        }
    };


    /* =====================================================
       NAVIGATION ACTIVE EFFECT
    ===================================================== */

    const navLinks =
        document.querySelectorAll(".navigation a");

    navLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            navLinks.forEach(function (item) {
                item.classList.remove("active");
            });

            this.classList.add("active");

        });

    });


    /* =====================================================
       CHANGE ACTIVE MENU WHILE SCROLLING
    ===================================================== */

    const sections =
        document.querySelectorAll("section[id]");

    window.addEventListener("scroll", function () {

        let current = "";

        sections.forEach(function (section) {

            const sectionTop =
                section.offsetTop - 150;

            const sectionHeight =
                section.offsetHeight;

            if (
                window.scrollY >= sectionTop &&
                window.scrollY < sectionTop + sectionHeight
            ) {

                current = section.getAttribute("id");

            }

        });


        navLinks.forEach(function (link) {

            link.classList.remove("active");

            if (
                link.getAttribute("href") === "#" + current
            ) {

                link.classList.add("active");

            }

        });

    });


    /* =====================================================
       SERVICE CARD CLICK EFFECT
    ===================================================== */

    const serviceCards =
        document.querySelectorAll(".service-card");

    serviceCards.forEach(function (card) {

        card.addEventListener("mouseenter", function () {

            this.style.cursor = "pointer";

        });

    });


    /* =====================================================
       HEADER SHADOW ON SCROLL
    ===================================================== */

    const header =
        document.querySelector(".header");

    window.addEventListener("scroll", function () {

        if (!header) {
            return;
        }

        if (window.scrollY > 20) {

            header.style.boxShadow =
                "0 6px 25px rgba(0,70,130,0.16)";

        } else {

            header.style.boxShadow =
                "0 4px 20px rgba(0,70,130,0.12)";

        }

    });


    /* =====================================================
       START PAGE FROM TOP
    ===================================================== */

    window.scrollTo(0, 0);

});