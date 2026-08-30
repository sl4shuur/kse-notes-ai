FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY mockup/assets/style.css /usr/share/nginx/html/assets/mockup.css
COPY web/index.html /usr/share/nginx/html/index.html
COPY web/app.css /usr/share/nginx/html/app.css
COPY web/app.js /usr/share/nginx/html/app.js
