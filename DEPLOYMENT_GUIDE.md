# InBrief Netlify + Supabase Deployment Guide

## ✅ Completed Setup
- ✅ Supabase database created and schema executed
- ✅ Netlify function configured for Supabase Session Pooler
- ✅ CORS headers and API endpoints ready

## 🚀 Deployment Steps

### 1. Deploy to Netlify

1. **Login to Netlify** (https://netlify.com)
   - Sign up/login with GitHub account (recommended)

2. **Deploy from folder** (drag and drop method):
   - Compress the entire `inbrief-backend` folder to a ZIP file
   - Go to Netlify dashboard
   - Drag and drop the ZIP file to deploy
   
   OR
   
   **Deploy from Git** (recommended):
   - Push your `inbrief-backend` folder to GitHub
   - Connect Netlify to your GitHub repository
   - Auto-deploy will handle the rest

### 2. Configure Environment Variables in Netlify

After deployment, you need to set the database connection string:

1. Go to your Netlify site dashboard
2. Click **Site Settings** → **Environment Variables**
3. Add a new variable:
   - **Key**: `SUPABASE_DATABASE_URL`
   - **Value**: `postgresql://postgres.iwzmixjdzjdukkrkwyxh:InBrief2025!@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`
   - **Database Name**: inbrief-database

### 3. Test Your Deployment

Once deployed, your Netlify site will have a URL like: `https://YOUR-SITE-NAME.netlify.app`

Test these endpoints:
- **Health Check**: `https://YOUR-SITE-NAME.netlify.app/`
- **Get News**: `https://YOUR-SITE-NAME.netlify.app/api/news/all`

### 4. Update Flutter App

After successful deployment, update your Flutter app:

In `lib/config/app_config.dart`:
```dart
class AppConfig {
  static const String apiBaseUrl = 'https://YOUR-SITE-NAME.netlify.app';
}
```

## 🔧 Connection String Details

You provided these connection options:

**✅ Using Session Pooler (CONFIGURED with your credentials):**
```
postgresql://postgres.iwzmixjdzjdukkrkwyxh:InBrief2025!@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

**Alternative options (backup):**
- Direct Connection: `postgresql://postgres:InBrief2025!@db.iwzmixjdzjdukkrkwyxh.supabase.co:5432/postgres`
- Transaction Pooler: `postgresql://postgres.iwzmixjdzjdukkrkwyxh:InBrief2025!@aws-0-ap-south-1.pooler.supabase.com:6543/postgres`

## 🎯 Why Session Pooler?

The Session Pooler is perfect for Netlify Functions because:
- ✅ Optimized for serverless environments
- ✅ Better connection management
- ✅ IPv4 compatible (as mentioned in your screenshot)
- ✅ Recommended for web applications

## 🔍 Troubleshooting

If deployment fails:
1. Check Netlify function logs in the dashboard
2. Verify the environment variable is set correctly
3. Ensure your Supabase password doesn't contain special characters that need escaping

## 📱 Testing on Mobile

Once deployed:
1. Update Flutter app with new Netlify URL
2. Build APK: `flutter build apk --release`
3. Test on problematic devices that had Railway issues

This setup should completely resolve the DNS blocking issues since:
- ✅ Netlify domains are widely accessible
- ✅ Supabase has global CDN and reliable connectivity
- ✅ No dependency on Railway infrastructure
