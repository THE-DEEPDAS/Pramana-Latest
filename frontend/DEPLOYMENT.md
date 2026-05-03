# Deployment Guide

This guide covers deploying PowerMind to various platforms.

## Prerequisites

- Node.js 18+ installed locally
- Git repository initialized
- npm/yarn/pnpm for dependency management

## Local Development

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Run development server:**
   ```bash
   npm run dev
   ```

3. **Open browser:**
   Navigate to `http://localhost:3000`

## Build for Production

```bash
npm run build
npm start
```

This creates an optimized production build.

## Vercel (Recommended for Next.js)

Vercel is the creator of Next.js and offers the best hosting experience.

### Deploy via Git

1. **Push to GitHub:**
   ```bash
   git push origin main
   ```

2. **Connect to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Select your GitHub repository
   - Click "Deploy"

### Environment Variables

1. In Vercel dashboard, go to project Settings
2. Navigate to "Environment Variables"
3. Add your environment variables:
   - `NEXT_PUBLIC_API_URL` (if needed)

### Deploy via CLI

```bash
npm install -g vercel
vercel login
vercel
```

## Docker Deployment

### Create Dockerfile

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Expose port
EXPOSE 3000

# Start application
CMD ["npm", "start"]
```

### Build and Run Docker Image

```bash
# Build image
docker build -t powermind:latest .

# Run container
docker run -p 3000:3000 powermind:latest
```

## AWS (EC2/ECS)

### EC2 Deployment

1. **SSH into EC2 instance:**
   ```bash
   ssh -i your-key.pem ec2-user@your-instance-ip
   ```

2. **Install Node.js:**
   ```bash
   curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
   sudo yum install -y nodejs
   ```

3. **Clone repository:**
   ```bash
   git clone your-repo-url
   cd powermind
   ```

4. **Install and build:**
   ```bash
   npm install
   npm run build
   ```

5. **Use PM2 for process management:**
   ```bash
   sudo npm install -g pm2
   pm2 start "npm start" --name "powermind"
   pm2 startup
   pm2 save
   ```

### Environment Variables

Create `.env.local`:
```bash
NEXT_PUBLIC_API_URL=your_api_url
```

## Netlify

1. **Connect GitHub repository:**
   - Go to [netlify.com](https://netlify.com)
   - Click "New site from Git"
   - Select your repository

2. **Build Settings:**
   - Build command: `npm run build`
   - Publish directory: `.next`

3. **Environment Variables:**
   - Add in Netlify Site Settings > Build & Deploy > Environment

## Railway

1. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login:**
   ```bash
   railway login
   ```

3. **Initialize and deploy:**
   ```bash
   railway init
   railway up
   ```

## Render

1. **Connect GitHub repository**
2. **Create Web Service:**
   - Build command: `npm install && npm run build`
   - Start command: `npm start`
   - Environment: Node 18

## Performance Optimization

### Before Deployment

1. **Optimize images:**
   - Use Next.js Image component
   - Compress assets

2. **Enable compression:**
   - Gzip is enabled by default in Next.js

3. **Code splitting:**
   - Automatic with Next.js

4. **Environment variables:**
   - Use `NEXT_PUBLIC_` prefix for client-side vars

### Monitoring

Add monitoring services:
- **Vercel Analytics** (automatic with Vercel)
- **Sentry** for error tracking
- **LogRocket** for session replay

## Environment Variables Template

```env
# API Configuration
NEXT_PUBLIC_API_URL=https://api.example.com

# Optional
DATABASE_URL=
API_SECRET_KEY=
```

## Security Checklist

- [ ] Environment variables are secured
- [ ] No sensitive data in code
- [ ] HTTPS enabled
- [ ] CORS configured properly
- [ ] CSP headers set
- [ ] Rate limiting implemented
- [ ] Input validation on all forms
- [ ] Output encoding for XSS prevention

## Troubleshooting

### Port 3000 in use
```bash
npm run dev -- -p 3001
```

### Build errors
```bash
rm -rf .next node_modules
npm install
npm run build
```

### Memory issues in CI
```bash
NODE_OPTIONS=--max-old-space-size=4096 npm run build
```

## Monitoring and Logs

### Vercel
- Dashboard shows real-time logs
- Automatic error tracking

### AWS CloudWatch
```bash
# View logs
aws logs tail /aws/lambda/powermind --follow
```

### Docker
```bash
docker logs container-id
docker logs -f container-id  # Follow logs
```

## Rollback

### Vercel
- Click "Deployments"
- Select previous deployment
- Click "Promote to Production"

### Docker/Manual
```bash
git revert commit-hash
npm run build
restart service
```

## Cost Optimization

- **Vercel**: Free tier includes generous limits
- **AWS**: Use spot instances for non-critical environments
- **Docker**: Choose appropriate instance size
- **Database**: Monitor query performance

## Support

For deployment issues:
- Check logs in deployment platform
- Verify environment variables
- Ensure Node version compatibility
- Check network connectivity

---

Need help? Check the [Next.js Deployment Docs](https://nextjs.org/docs/deployment)
