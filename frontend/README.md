# OratoAI Frontend

A React-based frontend for the OratoAI video analysis system.

## Features

- **Video Upload**: Drag & drop video file upload with validation
- **Real-time Status**: Live processing status updates
- **File Management**: Download and preview processed files
- **Responsive Design**: Modern, mobile-friendly interface
- **Error Handling**: Comprehensive error handling and user feedback

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Configuration

Create a `.env` file in the frontend directory:

```env
# API Configuration
REACT_APP_API_URL=http://localhost:8000

# Development settings
GENERATE_SOURCEMAP=false
```

### 3. Start Development Server

```bash
npm start
```

The application will open at `http://localhost:3000`

### 4. Build for Production

```bash
npm run build
```

## API Integration

The frontend integrates with the FastAPI backend through the following endpoints:

- `POST /api/v1/videos/upload` - Upload video file
- `GET /api/v1/videos/{submission_id}/status` - Get processing status
- `GET /api/v1/videos/{submission_id}/files` - Get file URLs

## Components

### VideoUpload
- File drag & drop interface
- Form validation
- Upload progress tracking
- User input for topic and user ID

### VideoStatus
- Real-time status monitoring
- File download/preview
- Auto-refresh for processing status
- Error handling and display

### Header
- Navigation between upload and status pages
- Branding and app information

## Styling

The application uses custom CSS with:
- Modern gradient backgrounds
- Card-based layout
- Responsive grid system
- Interactive buttons and forms
- Loading animations
- Status badges and alerts

## Dependencies

- **React 18**: UI framework
- **React Router**: Client-side routing
- **Axios**: HTTP client for API calls
- **React Dropzone**: File upload interface
- **React Toastify**: Toast notifications
- **Lucide React**: Icon library

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
