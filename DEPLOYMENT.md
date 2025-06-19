# WSP Optimizer Deployment Guide

## Overview
This guide covers deploying the WSP Optimizer web application to various platforms.

## Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   python -c "import nltk; nltk.download('stopwords')"
   ```

2. **Run locally:**
   ```bash
   python app.py
   ```
   Visit http://localhost:5000

## Docker Deployment

### Quick Start with Docker Compose

1. **Clone and configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your secret key
   ```

2. **Build and run:**
   ```bash
   docker-compose up --build
   ```
   Visit http://localhost

### Production Docker Deployment

1. **Build image:**
   ```bash
   docker build -t wsp-optimizer .
   ```

2. **Run container:**
   ```bash
   docker run -d \
     -p 5000:5000 \
     -e SECRET_KEY=your-secure-secret-key \
     -v $(pwd)/results:/app/results \
     -v $(pwd)/uploads:/app/uploads \
     --name wsp-optimizer \
     wsp-optimizer
   ```

## Cloud Deployment Options

### Heroku Deployment

1. **Create Heroku app:**
   ```bash
   heroku create your-wsp-optimizer
   ```

2. **Add Procfile:**
   ```bash
   echo "web: gunicorn app:app" > Procfile
   ```

3. **Deploy:**
   ```bash
   git add .
   git commit -m "Initial deployment"
   git push heroku main
   ```

4. **Set environment variables:**
   ```bash
   heroku config:set SECRET_KEY=your-secure-secret-key
   ```

### AWS EC2 Deployment

1. **Launch EC2 instance** (Ubuntu 20.04 recommended)

2. **SSH and install Docker:**
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose
   sudo usermod -aG docker $USER
   ```

3. **Clone repository:**
   ```bash
   git clone https://github.com/your-repo/wsp-optimizer.git
   cd wsp-optimizer
   ```

4. **Configure and run:**
   ```bash
   cp .env.example .env
   # Edit .env file
   sudo docker-compose up -d
   ```

5. **Configure security group:**
   - Allow HTTP (80) and HTTPS (443)
   - Allow SSH (22) from your IP only

### Google Cloud Run Deployment

1. **Build and push to Container Registry:**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT-ID/wsp-optimizer
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy --image gcr.io/PROJECT-ID/wsp-optimizer \
     --platform managed \
     --allow-unauthenticated \
     --memory 2Gi \
     --timeout 300
   ```

### DigitalOcean App Platform

1. **Create app.yaml:**
   ```yaml
   name: wsp-optimizer
   services:
   - name: web
     github:
       repo: your-username/wsp-optimizer
       branch: main
     build_command: pip install -r requirements.txt
     run_command: gunicorn app:app
     http_port: 5000
     instance_count: 1
     instance_size_slug: basic-xs
     envs:
     - key: SECRET_KEY
       value: your-secure-secret-key
       type: SECRET
   ```

2. **Deploy via CLI:**
   ```bash
   doctl apps create --spec app.yaml
   ```

## Production Considerations

### Security
- Always use HTTPS in production
- Set strong SECRET_KEY
- Configure CORS properly
- Use environment variables for sensitive data

### Performance
- Use Redis for job queue (optional):
  ```python
  # Add to app.py for Redis support
  from redis import Redis
  redis = Redis.from_url(os.environ.get('REDIS_URL'))
  ```

- Configure file storage (S3 recommended):
  ```python
  # For AWS S3 storage
  import boto3
  s3 = boto3.client('s3')
  ```

### Monitoring
- Set up application monitoring (New Relic, Datadog)
- Configure error tracking (Sentry)
- Set up log aggregation

### Scaling
- Use multiple workers:
  ```bash
  gunicorn --workers 4 --threads 2 app:app
  ```

- Configure autoscaling based on CPU/memory

### Backup
- Regular backup of results folder
- Database backups if using persistent storage

## SSL/HTTPS Setup

### Using Let's Encrypt with Docker

1. **Update docker-compose.yml:**
   ```yaml
   certbot:
     image: certbot/certbot
     volumes:
       - ./certbot/conf:/etc/letsencrypt
       - ./certbot/www:/var/www/certbot
   ```

2. **Obtain certificate:**
   ```bash
   docker-compose run certbot certonly --webroot \
     --webroot-path=/var/www/certbot \
     -d your-domain.com
   ```

### Using Cloudflare
1. Add your domain to Cloudflare
2. Enable "Full SSL/TLS encryption"
3. Configure origin certificate

## Maintenance

### Updates
```bash
git pull origin main
docker-compose down
docker-compose up --build -d
```

### Logs
```bash
docker-compose logs -f web
```

### Cleanup old results
```bash
# Add to crontab
0 2 * * * find /app/results -mtime +30 -type f -delete
```

## Troubleshooting

### Common Issues

1. **Upload fails:**
   - Check file size limits
   - Verify NGINX client_max_body_size

2. **Processing timeout:**
   - Increase gunicorn timeout
   - Check memory allocation

3. **Results not found:**
   - Check volume mounts
   - Verify file permissions

### Debug Mode
```bash
docker-compose exec web python app.py --debug
```

## Support
For deployment issues, check logs first:
```bash
docker-compose logs web
```