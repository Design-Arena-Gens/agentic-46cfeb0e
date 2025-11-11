from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build
import re
import os
from typing import Optional, List, Dict
import json

app = FastAPI(title="YouTube Comments API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# YouTube API key - should be set as environment variable
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_comments(video_id: str, max_results: int = 100) -> List[Dict]:
    """Fetch comments from YouTube video"""
    if not YOUTUBE_API_KEY:
        # Return mock data if no API key is set
        return [
            {
                "author": "Demo User",
                "text": "This is a demo comment. Set YOUTUBE_API_KEY environment variable to fetch real comments.",
                "likes": 0,
                "published_at": "2024-01-01T00:00:00Z",
                "reply_count": 0
            }
        ]

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

        comments = []
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=min(max_results, 100),
            order='relevance',
            textFormat='plainText'
        )

        response = request.execute()

        for item in response.get('items', []):
            comment = item['snippet']['topLevelComment']['snippet']
            comments.append({
                "author": comment['authorDisplayName'],
                "text": comment['textDisplay'],
                "likes": comment['likeCount'],
                "published_at": comment['publishedAt'],
                "reply_count": item['snippet']['totalReplyCount']
            })

        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching comments: {str(e)}")

@app.get("/")
def read_root():
    """Root endpoint with API information"""
    return {
        "name": "YouTube Comments API",
        "version": "1.0.0",
        "endpoints": {
            "/comments": "GET - Fetch YouTube comments",
            "/health": "GET - Health check"
        },
        "example": "/comments?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&max_results=50"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "api_key_configured": bool(YOUTUBE_API_KEY)
    }

@app.get("/comments")
def get_comments(
    url: str = Query(..., description="YouTube video URL or video ID"),
    max_results: int = Query(100, ge=1, le=100, description="Maximum number of comments to fetch")
):
    """
    Fetch comments from a YouTube video

    Parameters:
    - url: YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID) or video ID
    - max_results: Maximum number of comments to return (1-100, default: 100)

    Returns:
    - video_id: Extracted video ID
    - comment_count: Number of comments returned
    - comments: List of comment objects
    """
    video_id = extract_video_id(url)

    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL or video ID. Please provide a valid YouTube video URL."
        )

    comments = get_youtube_comments(video_id, max_results)

    return {
        "video_id": video_id,
        "comment_count": len(comments),
        "comments": comments
    }

@app.get("/video/{video_id}/comments")
def get_comments_by_id(
    video_id: str,
    max_results: int = Query(100, ge=1, le=100, description="Maximum number of comments to fetch")
):
    """
    Fetch comments from a YouTube video by video ID

    Parameters:
    - video_id: YouTube video ID
    - max_results: Maximum number of comments to return (1-100, default: 100)
    """
    if len(video_id) != 11:
        raise HTTPException(
            status_code=400,
            detail="Invalid video ID format. YouTube video IDs are 11 characters long."
        )

    comments = get_youtube_comments(video_id, max_results)

    return {
        "video_id": video_id,
        "comment_count": len(comments),
        "comments": comments
    }
