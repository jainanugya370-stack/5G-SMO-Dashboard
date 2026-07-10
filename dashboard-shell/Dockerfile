FROM nginx:alpine

# Copy dashboard-shell static files to nginx web root
COPY . /usr/share/nginx/html/

# Remove the default nginx config and use a minimal one
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
