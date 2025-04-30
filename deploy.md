# Deployment Instructions

Follow these steps to redeploy your updated API with CORS support:

## 1. Commit Changes

```
git add serverless_main.py
git commit -m "Add CORS middleware to allow cross-origin requests"
```

## 2. Push to Your Repository

```
git push
```

## 3. Trigger Vercel Redeployment

If you've set up continuous deployment, Vercel will automatically redeploy when you push to your repository.

If not, you can manually redeploy from the Vercel dashboard:
1. Go to https://vercel.com/dashboard
2. Select your project
3. Click on the "Deployments" tab
4. Click "Redeploy" on your latest deployment

## 4. Alternative: Deploy from CLI

If you have the Vercel CLI installed:

```
vercel --prod
```

## 5. Verify CORS is Working

After redeployment, test by embedding your chat widget on a different domain or using a simple test like:

```javascript
fetch('https://chatwithwebsite-lyart.vercel.app/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    url: 'https://example.com',
    message: 'Hello'
  })
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
``` 