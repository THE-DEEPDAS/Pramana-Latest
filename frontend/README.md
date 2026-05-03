# PowerMind - RAG Assistant Frontend

A clean, minimal, and production-ready frontend template for a Retrieval-Augmented Generation (RAG) application. Built with Next.js 14, React 18, and Tailwind CSS.

## Features

### 📁 File Upload Section
- **Drag & drop upload area** - Intuitive file upload with visual feedback
- **Upload button** - Alternative file selection method
- **File list with status** - Track upload progress and completion
- **File management** - Delete and organize uploaded documents
- **Supported formats** - PDF, TXT, DOCX

### 💬 QnA Chatbot Interface
- **Chat-style conversation** - Modern message layout
- **User and AI message bubbles** - Visual distinction between user and assistant
- **Real-time input** - Textarea with keyboard shortcuts (Enter to send, Shift+Enter for newline)
- **Loading/thinking state** - Animated loading indicator
- **Timestamp tracking** - Messages are timestamped
- **Auto-scroll** - Automatically scrolls to latest message

### 🧭 Sidebar Navigation
- **App branding** - PowerMind logo and title
- **Tab navigation** - Easy switching between Upload and Chat
- **Document counter** - Shows indexed documents count
- **Settings panel** - Placeholder for future settings
- **Expandable sections** - Room for additional features

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS 3.4
- **Icons**: Lucide React
- **Language**: TypeScript
- **Package Manager**: npm/yarn/pnpm

## Project Structure

```
powermind/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Main page component
│   └── globals.css         # Global styles with Tailwind
├── components/
│   ├── Sidebar.tsx         # Navigation sidebar
│   ├── MainContent.tsx     # Main content wrapper
│   ├── FileUploadSection.tsx # File upload UI
│   └── ChatInterface.tsx    # Chat interface
├── package.json            # Dependencies
├── next.config.js          # Next.js config
├── tailwind.config.js      # Tailwind config
├── tsconfig.json           # TypeScript config
└── postcss.config.js       # PostCSS config
```

## Design Features

### Color Palette
- **Background**: Deep slate (#0f172a)
- **Cards**: Dark slate (#1e293b)
- **Text**: Off-white (#f8fafc)
- **Muted Text**: Light slate (#94a3b8)
- **Accent**: Bright blue (#3b82f6)
- **Status Colors**: Green (#10b981) for success, Red (#ef4444) for errors

### Design Principles
- ✨ Clean, minimal aesthetic
- 🎨 Developer-friendly dark mode
- 📱 Fully responsive design
- ♿ Semantic HTML structure
- ⚡ Performance optimized
- 🎯 Subtle shadows and borders
- 📏 Consistent spacing and alignment

## Getting Started

### Prerequisites
- Node.js 18+ (LTS recommended)
- npm, yarn, pnpm, or bun

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

2. **Run development server:**
   ```bash
   npm run dev
   # or
   yarn dev
   # or
   pnpm dev
   ```

3. **Open in browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

### Build for Production

```bash
npm run build
npm start
```

## Component Guide

### Sidebar
- Displays app branding and navigation
- Active tab highlighting
- Document count status
- Settings placeholder

**Props:**
- `activeTab` - Current tab ('chat' | 'upload')
- `setActiveTab` - Function to change active tab

### FileUploadSection
- Drag and drop file upload
- File list with upload status
- File deletion capability
- Progress tracking

**Features:**
- Simulates 2-second upload delay
- Status indicators (uploading, completed, failed)
- File size formatting
- Timestamp tracking

### ChatInterface
- Message history display
- User and assistant message distinction
- Real-time message sending
- Loading animation
- Keyboard shortcuts (Enter to send)

**Features:**
- Auto-scrolling to latest message
- Timestamp for each message
- Disabled input during loading
- Multi-line input support

## Customization

### Changing Colors
Edit `tailwind.config.js` to modify the color palette:

```javascript
colors: {
  background: '#0f172a',
  foreground: '#f8fafc',
  // ... customize colors
}
```

### Adding New Pages
Create new files in the `app/` directory following Next.js App Router conventions.

### Creating Components
Add new reusable components to the `components/` directory and import them where needed.

## Integration Tips

### Connecting to Your Backend
1. Replace the simulated API calls in `ChatInterface.tsx` with actual backend requests:
   ```typescript
   const response = await fetch('/api/chat', {
     method: 'POST',
     body: JSON.stringify({ message: input })
   })
   ```

2. Update file upload in `FileUploadSection.tsx` to post to your backend:
   ```typescript
   const formData = new FormData()
   formData.append('file', file)
   await fetch('/api/upload', { method: 'POST', body: formData })
   ```

### Adding Authentication
- Use Next.js middleware for route protection
- Add auth provider (NextAuth.js, Clerk, etc.)
- Protect API routes

### Database Integration
- Connect to your vector database
- Use server components for data fetching
- Implement document indexing

## Performance Optimizations

- ✅ Image optimization (Next.js Image component)
- ✅ Code splitting (automatic with Next.js)
- ✅ CSS purging (Tailwind)
- ✅ Responsive design (mobile-first)
- ✅ Semantic HTML for accessibility

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line in chat input |
| `Tab` | Navigate between elements |

## Future Enhancements

- [ ] User authentication and profiles
- [ ] Document management dashboard
- [ ] Advanced search and filtering
- [ ] Citation and source tracking
- [ ] Export conversation feature
- [ ] Dark/light mode toggle
- [ ] Conversation history
- [ ] Settings panel with preferences
- [ ] Multi-language support
- [ ] Analytics and usage tracking

## Troubleshooting

### Port 3000 already in use
```bash
npm run dev -- -p 3001
```

### Clear cache and reinstall
```bash
rm -rf node_modules .next
npm install
npm run dev
```

### TypeScript errors
```bash
npm run build
```

## License

MIT - Feel free to use this template for your projects

## Support

For issues and questions, create an issue in the repository or contact the team.

---

**Ready for hackathon demos!** 🚀
