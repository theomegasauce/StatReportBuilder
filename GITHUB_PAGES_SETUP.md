# GitHub Pages Setup for StatReportBuilder

This guide explains how to enable and configure GitHub Pages for this project.

## Prerequisites

- Your repository is on GitHub
- You have admin access to the repository settings

## Setup Steps

### 1. Enable GitHub Pages in Repository Settings

1. Go to your repository on GitHub
2. Click **Settings** (gear icon)
3. Navigate to **Pages** (in the left sidebar under "Code and automation")
4. Under "Build and deployment":
   - **Source**: Select "Deploy from a branch"
   - **Branch**: Select `main` (or your main branch)
   - **Folder**: Select `/docs`
   - Click **Save**

### 2. Wait for Deployment

GitHub will automatically build and deploy your site. You should see:
- A message: "Your site is live at `https://username.github.io/StatReportBuilder/`"
- A green checkmark next to the commit when complete (usually within 1-2 minutes)

### 3. Verify Your Site

- Visit `https://username.github.io/StatReportBuilder/` in your browser
- You should see the StatReportBuilder landing page

## What's Included

- **`docs/index.html`** - Main landing page with:
  - Project overview
  - Feature highlights
  - Download instructions
  - Developer setup guide
  - Contributing guidelines
  - Responsive design for mobile and desktop

- **`docs/.nojekyll`** - Tells GitHub to serve files as-is (optional but recommended)

## Customization

### Update Links
Edit `docs/index.html` to customize:
- GitHub repository URL
- Release download links
- Social media links
- Contact information

### Change Colors
Modify the CSS gradient in the `<style>` section:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Add More Pages
Create additional HTML files in the `docs/` folder:
- `docs/features.html` - Detailed feature descriptions
- `docs/changelog.html` - Version history
- `docs/faq.html` - Frequently asked questions

## Troubleshooting

### Site Not Showing Up
- Check that the branch is `main` (or your actual main branch)
- Verify the folder is `/docs`
- Clear your browser cache or use an incognito window
- Check the "Actions" tab for deployment errors

### Custom Domain
To use a custom domain (e.g., `statreportbuilder.com`):
1. In Repository Settings → Pages
2. Under "Custom domain", enter your domain
3. Update your DNS provider to point to GitHub Pages IP addresses
4. See [GitHub documentation](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site) for details

## Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Custom domains](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)
