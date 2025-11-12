# 🎉 Voilà Voice Dashboard - Next.js Version

A modern, professional dashboard for managing voice agent operations with Google-level UI/UX design.

## 📸 Features

- **Clean & Minimalistic Design** - Google-level UI/UX
- **Fully Responsive** - Works on mobile, tablet, and desktop
- **Professional Icons** - Lucide React icons throughout
- **Micro-Interactions** - Hover effects, animations, transitions
- **7 Complete Pages** - All fully functional with dummy data
- **TypeScript** - Type-safe code throughout
- **Tailwind CSS 4** - Modern styling
- **Shadcn UI** - Beautiful component library

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open browser
http://localhost:3000
```

## 📄 Pages

### 1. **Home Page** (/)
- Hero section with features
- Auto-redirects to login after 5 seconds
- Beautiful animations

### 2. **Login Page** (/login)
- Split-screen design
- Accepts ANY credentials (for demo)
- Clean, professional layout

### 3. **Dashboard** (/dashboard)
- 4 stat cards (Minutes, Revenue, Calls, Avg Duration)
- Region and date range filters
- 6 beautiful charts (Recharts)
- Recent calls table with pagination
- Call details modal with tabs

### 4. **Q&A Management** (/dashboard/conoscenza)
- Region-based knowledge management
- Add/Edit/Delete Q&A entries
- Search and sort functionality
- Card-based display with hover effects

### 5. **User Management** (/dashboard/utenti)
- Create new users
- Users table with search/filter
- Toggle user status
- Resend credentials
- Delete users

### 6. **Voice Agent Control** (/dashboard/voiceagent)
- Toggle voice agents by region
- Real-time statistics
- System status overview
- Configuration notes

### 7. **Chat Interface** (/dashboard/verifica-conoscenza)
- Modern chat UI
- Message history
- Function call indicators (RAG/GRAPH)
- Character counter
- Auto-scroll

## 🎨 Design Features

### Micro-Interactions
- `hover:scale-105` on buttons
- `hover:-translate-y-1` on cards (lift effect)
- `hover:shadow-md` on interactive elements
- Border color transitions
- Smooth animations

### Professional Icons
- No emojis - all Lucide icons
- Icons in headers, badges, buttons
- Color-coded icons
- Consistent icon sizing

### Color Palette
- **Primary:** Blue (#3b82f6)
- **Success:** Green (#10b981)
- **Warning:** Yellow (#f59e0b)
- **Danger:** Red (#ef4444)
- **Purple:** #9333ea (RAG)
- **Borders:** Light gray (rgb(229, 231, 235))

## 🛠️ Tech Stack

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS 4
- **Components:** Shadcn UI
- **Charts:** Recharts
- **Icons:** Lucide React
- **State:** React Hooks

## 📁 Project Structure

```
new-version/
├── app/
│   ├── (auth)/login/          # Login page
│   ├── (dashboard)/
│   │   ├── layout.tsx          # Dashboard layout with sidebar
│   │   ├── dashboard/          # Main dashboard
│   │   ├── conoscenza/         # Q&A management
│   │   ├── utenti/             # User management
│   │   ├── voiceagent/         # Voice agent control
│   │   └── verifica-conoscenza/ # Chat interface
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Hero landing page
│   └── globals.css             # Global styles
├── components/
│   ├── layout/                 # Sidebar, Navbar
│   ├── dashboard/              # Dashboard components
│   └── ui/                     # Shadcn UI components
├── lib/
│   ├── dummy-data.ts           # Mock data
│   └── utils.ts                # Utility functions
├── types/
│   └── index.ts                # TypeScript definitions
└── public/
    └── images/                 # Logos and images
```

## 📊 Dummy Data

All pages currently use dummy data from `lib/dummy-data.ts`:

- `dummyRegions` - Available regions
- `dummyDashboardStats` - Dashboard statistics
- `dummySentimentStats` - Sentiment distribution
- `dummyActionStats` - Action distribution
- `dummyRecentCalls` - 100 mock calls
- `dummyQAEntries` - Sample Q&A
- `dummyUsers` - Sample users
- `dummyChatMessages` - Sample chat messages

## 🔐 Authentication

**Current (Demo):**
- Login accepts ANY email and password
- No real authentication
- Demo purposes only

**For Production:**
- Replace with real API calls to backend
- Implement JWT token handling
- Add proper session management

## 🔗 Backend Integration

The application is ready to connect to the FastAPI backend:

**Backend Location:** `../app.py`
**Port:** 8745
**Database:** MySQL (voila_tech_voice)

### To Integrate:
1. Create `lib/api.ts` with fetch functions
2. Replace dummy data imports with API calls
3. Add error handling
4. Implement authentication flow

## 📝 Available Scripts

```bash
# Development
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## 🎯 Key Features

### Responsive Design
- Mobile-first approach
- Sidebar becomes hamburger menu on mobile
- Tables scroll horizontally on small screens
- Grid layouts adapt to screen size

### Accessibility
- Semantic HTML
- ARIA labels
- Keyboard navigation
- Screen reader friendly

### Performance
- Optimized images with Next.js Image
- Code splitting
- Lazy loading
- Fast page transitions

## 📖 Documentation

See `WHATS_DONE.MD` for complete documentation including:
- Detailed feature list
- Design specifications
- Implementation notes
- Future integration steps

## 🚀 Deployment

```bash
# Build the application
npm run build

# Test production build
npm start
```


For questions or issues, please refer to the documentation in `WHATS_DONE.MD`.
