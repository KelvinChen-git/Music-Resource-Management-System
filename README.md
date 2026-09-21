# Music Resource Management System

A full-stack web application for uploading, organizing, discovering, reviewing, playing, and downloading music resources.

The system provides separate workflows for regular users and administrators, combining resource management, multi-criteria search, role-based access control, approval management, and user interaction features in a unified platform.

## Overview

Managing a growing music collection involves more than storing audio files. Users need to organize resources with categories and tags, locate music through flexible search criteria, track their interactions, and control how files are shared.

This project addresses those requirements through a Vue-based frontend, a Spring Boot backend, and a MySQL database. It supports the complete resource lifecycle, from uploading an MP3 file and editing its metadata to administrative approval, playback, download, soft deletion, and recovery.

The system was developed between **March 2025 and July 2025** as a full-stack software engineering project.

## Key Features

### User Authentication

- User registration and login
- JWT-based authentication
- Email verification
- Password modification
- Role and account-status management
- Authenticated access to user-specific resources and actions

### Music Resource Management

- Upload MP3 files up to 20 MB
- Create and edit music metadata
- Assign categories and tags
- View resource details
- Play music through the web interface
- Download individual approved resources
- Export selected resources as a ZIP archive with JSON metadata
- Soft-delete resources
- Recover deleted resources
- Permanently delete resources when authorized

### Search and Filtering

The platform supports combined search across several dimensions:

- Keywords
- Categories
- Tags
- Uploaders
- Upload dates
- Approval status

The backend builds queries with MyBatis dynamic SQL rather than maintaining separate hard-coded queries for every filter combination.

Search behavior includes:

- Fuzzy matching across supported text fields
- Combined keyword, category, and tag filtering
- Tag-intersection queries
- Uploader and upload-time filters
- Approval-status filtering
- Pagination
- Clear-filter and reset behavior
- Explicit no-result feedback
- Locally cached search history
- Reactive result updates without a full-page reload

The frontend synchronizes filter state with the page URL, allowing search conditions to remain consistent during navigation and page refreshes.

## User Interaction

Registered users can interact with resources through:

- Comments
- Likes
- Favorites
- Playback history
- Personal upload management
- Search-history records

These features connect user activity with the corresponding music resource while keeping authentication and resource visibility rules enforced by the backend.

## Administrative Workflow

Administrators can:

- Review submitted music resources
- Approve or reject uploads
- View resources from all uploaders
- Manage users, roles, and account status
- Access resources in every approval state
- Restore or permanently remove deleted records
- Review metadata before a resource becomes downloadable

Uploaded resources move through an approval workflow:

```text
Upload → Pending Review → Approved / Rejected
```

The approval state controls which actions are available to regular users.

## Access-Control Rules

| Resource status | Regular user: Play | Regular user: Download | Administrator |
|---|---:|---:|---:|
| Approved | Yes | Yes | Full access |
| Pending | Yes | No | Full access |
| Rejected | No | No | Full access |

The frontend provides status-specific prompts, while the backend applies the corresponding authorization rules to protected operations.

Frontend restrictions are used for user guidance; access decisions are enforced by backend endpoints.

## System Architecture

```text
┌─────────────────────────────────────┐
│        Vue 3 Web Application        │
│ Composition API · Pinia · Axios     │
│ Element Plus                        │
└──────────────────┬──────────────────┘
                   │ JSON REST API
                   ▼
┌─────────────────────────────────────┐
│       Spring Boot Application       │
│ Authentication · Business Logic     │
│ Validation · Resource Management    │
└──────────────┬───────────┬──────────┘
               │           │
               ▼           ▼
┌────────────────────┐  ┌────────────────────┐
│       MyBatis      │  │ Local File Storage │
│ Dynamic SQL        │  │ Audio and Images   │
└──────────┬─────────┘  └──────────┬─────────┘
           │                       │
           ▼                       │
┌────────────────────┐             │
│       MySQL        │◄────────────┘
│ Metadata and State │
└────────────────────┘
```

The frontend communicates with the backend through JSON REST interfaces. Music files and images are stored on the server and accessed through backend-managed URLs, while MySQL stores users, metadata, categories, tags, approval states, and interaction records.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Vue 3, Composition API, Pinia, Axios, Element Plus |
| Backend | Java 17, Spring Boot, Spring MVC, MyBatis |
| Database | MySQL |
| Authentication | JWT, email verification |
| API documentation | Swagger |
| Build tool | Maven |
| File storage | Server-local storage |
| Deployment environment | Alibaba Cloud ECS |

## Backend Design

### REST API

The backend exposes JSON REST interfaces for:

- Authentication and account management
- Music-resource creation, retrieval, update, and deletion
- Category and tag management
- Search and pagination
- File upload, playback, and download
- Approval-state transitions
- Comments, likes, favorites, and playback records
- Administrative user and resource management

Swagger is used to document endpoints, inspect request and response structures, and manually validate API behavior during development.

### Dynamic Search

Search conditions are translated into MyBatis dynamic SQL based on the filters supplied by the frontend.

For example, a request may combine:

```text
keyword + category + multiple tags + uploader + date range + approval status
```

Only applicable SQL clauses are added to the query. This avoids creating a separate endpoint for every possible filter combination and keeps filtering logic centralized in the backend.

Tag filtering uses the many-to-many relationship between music resources and tags. Combined filters preserve pagination and return results satisfying the selected conditions.

### Data Relationships

The central domain objects include:

- User
- Music resource
- Category
- Tag
- Comment
- Like
- Favorite
- Playback record

A music resource belongs to an uploader and can be associated with a category and multiple tags. Interaction records connect authenticated users with individual resources.

The resource–tag relationship is modeled separately to support many-to-many associations and multi-tag filtering.

### Resource Lifecycle

A music resource passes through several stages:

1. A user uploads an MP3 file and enters its metadata.
2. The backend validates the request and stores the file.
3. Metadata and file-location information are saved in MySQL.
4. The resource enters the pending state.
5. An administrator reviews the submission.
6. The administrator approves or rejects the resource.
7. Approved resources become available for playback and download.
8. Deleted resources remain recoverable until permanent deletion.

Soft deletion separates accidental removal from irreversible deletion and allows authorized users to recover resources.

## Frontend Design

The Vue frontend uses the Composition API to organize page-level logic and reusable state.

Pinia manages shared application state such as:

- Authentication status
- Current user information
- Search filters
- Resource lists
- Pagination
- Approval state
- User-facing notifications

Axios handles communication with the backend REST API.

Search controls update the visible results without reloading the whole page. Filter values are synchronized with the URL so that navigation does not unexpectedly reset the search state.

The interface also provides:

- Clear-filter actions
- Empty-result messages
- Approval-status prompts
- Upload validation feedback
- Role-specific actions
- Playback and download controls

## File Handling

The system supports MP3 uploads with a maximum file size of 20 MB.

The backend is responsible for:

- Validating uploaded files
- Saving audio files and related images
- Recording their server locations
- Returning controlled access URLs
- Streaming files for playback
- Serving authorized downloads
- Packaging selected resources into ZIP archives
- Exporting associated metadata as JSON

File operations are connected to database records so that metadata and stored resources remain associated throughout approval, deletion, and recovery workflows.

## API Validation

REST interfaces were documented and manually validated with Swagger.

Validation focused on representative workflows such as:

- Successful and failed authentication
- Resource creation and metadata updates
- Combined search filters
- Pagination
- Approval-state transitions
- Role-specific playback and download behavior
- Soft deletion and recovery
- Invalid or unauthorized requests

Swagger-based validation verifies endpoint behavior interactively. It should not be interpreted as automated unit or integration test coverage.

## My Contribution

I independently developed the application end to end, including:

- Designing the MySQL data model
- Implementing the Spring Boot and MyBatis backend
- Building JSON REST interfaces
- Implementing JWT authentication and account workflows
- Developing the Vue 3 and Pinia frontend
- Building multi-criteria search with MyBatis dynamic SQL
- Synchronizing frontend filter state with the URL
- Implementing resource upload, playback, and download
- Implementing category and tag management
- Implementing the administrative approval workflow
- Adding comments, likes, favorites, and playback records
- Documenting and manually validating APIs with Swagger
- Deploying the application environment on Alibaba Cloud ECS

## Engineering Challenges

### Supporting flexible combined search

Users may provide only one filter or combine several filters in the same request. Dynamic SQL was used to construct only the necessary query conditions while preserving pagination and consistent results.

### Keeping frontend and backend filter state aligned

Search conditions can become inconsistent when the user navigates between pages or refreshes the browser. The frontend synchronizes reactive filter state with URL parameters and restores the corresponding search state when needed.

### Enforcing approval-dependent actions

Playback and download permissions depend on both the user role and resource status. The system applies these rules in backend operations and mirrors them in the frontend through status-specific controls and messages.

### Managing file and metadata lifecycles

Audio files, images, database metadata, and approval state must remain associated during updates, deletion, and recovery. The resource workflow keeps these elements connected through stored identifiers and backend-managed file URLs.


## Possible Future Improvements

- Add automated unit and integration tests
- Move media files to object storage
- Add asynchronous media-processing jobs
- Generate waveform previews and audio metadata automatically
- Introduce database query and index benchmarks
- Add structured logging and monitoring
- Add CI/CD workflows
- Containerize the frontend, backend, and database
- Improve accessibility and mobile layouts

These items are future development directions and are not included in the completed feature claims above.
