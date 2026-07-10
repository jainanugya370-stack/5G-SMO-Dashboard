FROM nginx:alpine

# Copy topology static files to nginx web root
COPY . /usr/share/nginx/html/

# Remove the default nginx config
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
