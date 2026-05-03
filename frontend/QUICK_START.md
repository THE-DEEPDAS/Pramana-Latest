# Quick Start Guide

Get PowerMind running in 5 minutes!

## 1. Prerequisites

- **Node.js**: 18.0.0 or higher ([download](https://nodejs.org/))
- **npm/yarn/pnpm**: Comes with Node.js or install separately
- **Git**: For cloning the repository

**Verify installation:**
```bash
node --version  # Should be v18+
npm --version   # Should be 8+
```

## 2. Installation (Choose one method)

### Method A: Clone from GitHub
```bash
git clone <your-repo-url>
cd Powermind
npm install
```

### Method B: From existing folder
```bash
cd Powermind
npm install
```

## 3. Run Development Server

```bash
npm run dev
```

You'll see:
```
▲ Next.js 14.2.3
- Local:        http://localhost:3000
- Environments: .env.local
```

## 4. Open in Browser

Navigate to: **http://localhost:3000**

You should see:
- 🎨 Dark-themed interface
- 📁 File upload section (default tab)
- 💬 Chat interface (click Chat in sidebar)
- 🧭 Navigation sidebar

## 5. Test the Interface

### Try File Upload:
1. Click the upload area or select "Upload Documents"
2. Drag and drop a file OR click "Select Files"
3. Watch the upload progress
4. See the file appear in the list

### Try Chat:
1. Click "Chat" in the sidebar
2. Type a message like "Hello"
3. Press Enter or click send
4. See the simulated response

## 6. Customize (Optional)

### Change App Title
Edit `components/Sidebar.tsx`:
```typescript
<h1 className="text-lg font-semibold text-[#f8fafc]">Your App Name</h1>
```

### Change Colors
Edit `tailwind.config.js`:
```javascript
colors: {
  'accent-blue': '#your-color',
}
```

### Add Your Logo
Replace the icon in `components/Sidebar.tsx`:
```typescript
<YourCustomIcon className="w-6 h-6" />
```

## 7. Connect to Your Backend

See [RAG_INTEGRATION.md](./RAG_INTEGRATION.md) for:
- Backend requirements
- API endpoint setup
- Integration examples
- Testing guide

**Quick example:**
```typescript
// In components/ChatInterface.tsx
const response = await fetch('http://your-backend:8000/api/chat', {
  method: 'POST',
  body: JSON.stringify({ message: input })
})
```

## 8. Build for Production

```bash
npm run build  # Creates optimized build
npm start      # Runs production server
```

## 9. Deploy

### Quick Deploy to Vercel (Recommended)
```bash
npm install -g vercel
vercel
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for other options.

## 10. Troubleshooting

### Port 3000 already in use?
```bash
npm run dev -- -p 3001
```

### Module not found?
```bash
rm -rf node_modules
npm install
```

### TypeScript errors?
```bash
npm run build  # Full type checking
```

## Project Structure

```
Powermind/
├── app/                    # Next.js app directory
│   ├── api/               # API routes
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Main page
│   └── globals.css        # Global styles
├── components/            # Reusable components
│   ├── Sidebar.tsx
│   ├── ChatInterface.tsx
│   ├── FileUploadSection.tsx
│   └── ...more components
├── lib/                   # Utilities
│   ├── types.ts          # TypeScript types
│   ├── utils.ts          # Helper functions
│   ├── hooks.ts          # Custom hooks
│   └── constants.ts      # App constants
├── package.json          # Dependencies
├── tailwind.config.js    # Tailwind config
├── tsconfig.json         # TypeScript config
└── README.md             # Full documentation
```

## Key Files to Edit

| File | Purpose |
|------|---------|
| `components/ChatInterface.tsx` | Chat logic and UI |
| `components/FileUploadSection.tsx` | File upload logic |
| `lib/api.ts` | Backend API calls |
| `tailwind.config.js` | Color scheme |
| `app/page.tsx` | Main layout |

## Common Commands

```bash
# Development
npm run dev              # Start dev server
npm run build           # Build for production
npm start               # Start production server

# Code Quality
npm run lint            # Check for issues
npm run build           # Full type checking
```

## Next Steps

1. ✅ [Integrate your RAG backend](./RAG_INTEGRATION.md)
2. ✅ [Customize the UI](./README.md#customization)
3. ✅ [Deploy to production](./DEPLOYMENT.md)
4. ✅ [Add authentication](./README.md#adding-authentication)
5. ✅ [Monitor performance](./DEPLOYMENT.md#monitoring-and-logs)

## Resources

- 📚 [Next.js Documentation](https://nextjs.org/docs)
- 🎨 [Tailwind CSS Docs](https://tailwindcss.com/docs)
- 💬 [React Hooks Guide](https://react.dev/reference/react)
- 🔧 [Lucide Icons](https://lucide.dev)

## Need Help?

- Check the [README.md](./README.md) for detailed docs
- Review [RAG_INTEGRATION.md](./RAG_INTEGRATION.md) for backend setup
- See [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment options
- Create an issue in the repository

## Tips

💡 **Pro Tips:**
- Use Ctrl+Shift+P (Cmd+Shift+P on Mac) in VS Code to run commands
- VS Code extensions recommended in `.vscode/extensions.json`
- Hot reload works automatically - just save files
- Tailwind IntelliSense helps with class names

---

**You're all set! Happy coding! 🚀**

Questions? Check the documentation files or create an issue.
