# API Reference (v1)

Base URL: `/api/v1/`

---

## 🔐 Authentication Endpoints

| Method | Endpoint | Description |
|---------|-----------|-------------|
| POST | `/accounts/register/` | Register new user |
| POST | `/accounts/login/` | Login with email and password |
| POST | `/accounts/logout/` | Logout and blacklist token |
| POST | `/accounts/token/refresh/` | Refresh access token |
| GET  | `/accounts/get-user/` | Get current user details |
| PUT  | `/accounts/update_user/` | Update user profile |
| DELETE | `/accounts/delete_user/` | Delete user account |
| POST | `/accounts/get-otp/` | Generate & Send OTP for email/phone verification |
| POST | `/accounts/verify-otp/` | Verify OTP for email/phone |
| POST | `/accounts/verify-otp/login/` | Login using OTP |
| POST | `/accounts/forgot-password/request/` | Request password reset (sends OTP) |
| POST | `/accounts/forgot-password/verify/` | Verify OTP for password reset |
| PUT  | `/accounts/forgot-password/reset/` | Reset password with verification token |

**Register Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Register Response (201):**
```json
{
  "message": "User created successfully",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_phone_verified": false,
    "date_joined": "2024-01-15T10:30:00Z"
  },
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

**Authentication Headers:**
```
Authorization: Bearer <access_token>
```

**Note**: All endpoints except register, login, and password reset require JWT authentication via Authorization header.

---

## 🏢 Organizations

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/organizations/get-org/` | List all organizations user is member of |
| POST | `/organizations/create-org/` | Create a new organization |
| GET  | `/organizations/get-org-details/` | Get organization details |
| PUT  | `/organizations/update-org/` | Update organization details |
| DELETE | `/organizations/delete-org/` | Delete organization (owner only) |
| GET  | `/organizations/get-org-members/` | List all organization members |
| POST | `/organizations/sent-invite/` | Send invite to user for organization |
| POST | `/organizations/accept-org-invite/` | Accept organization invite |
| PUT  | `/organizations/update-member/` | Update member role in organization |
| DELETE | `/organizations/remove-member/` | Remove member from organization |
| DELETE | `/organizations/self-remove-member/` | Remove yourself from organization |
| PUT  | `/organizations/update-owner/` | Transfer organization ownership |

**Query Parameters:**
- `org_id` - Organization ID (required for most operations)
- `email` - User email (for member operations)
- `role` - Role to assign (OWNER, ADMIN, MANAGER, MEMBER, VIEWER)
- `search` - Search by name
- `ordering` - Order by field (-created_at)

**Create Organization Request Body:**
```json
{
  "name": "Acme Corporation"
}
```

**Create Organization Response (201):**
```json
{
  "message": "Organization created successfully",
  "data": {
    "id": "org-uuid",
    "name": "Acme Corporation",
    "owner": "user-uuid",
    "member_count": 1,
    "team_count": 0,
    "project_count": 0,
    "owner_email": "owner@example.com",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Organization Roles:**
- `OWNER` - Root-level access, created the org
- `ADMIN` - Full control except deleting org
- `MANAGER` - Manage teams/projects but not billing
- `MEMBER` - Normal user
- `VIEWER` - Read-only access

---

## � Teams

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/teams/get-user-teams/` | List all teams user is member of |
| POST | `/teams/create-team/` | Create a new team |
| GET  | `/teams/get-team-details/` | Get team details |
| PUT  | `/teams/update-team/` | Update team details |
| DELETE | `/teams/delete-team/` | Delete team (creator only) |
| GET  | `/teams/get-org-teams/` | List all teams in an organization |
| GET  | `/teams/get-team-members/` | List all team members |
| POST | `/teams/sent-invite/` | Send invite to user for team |
| POST | `/teams/accept-team-invite/` | Accept team invite |
| PUT  | `/teams/update-member/` | Update member role in team |
| DELETE | `/teams/remove-member/` | Remove member from team |
| DELETE | `/teams/self-remove-member/` | Remove yourself from team |
| PUT  | `/teams/transfer-owner/` | Transfer team ownership |

**Query Parameters:**
- `team_id` - Team ID (required for most operations)
- `org_id` - Organization ID (for org_teams endpoint)
- `email` - User email (for member operations)
- `role` - Role to assign (OWNER, MANAGER, LEAD, MEMBER, VIEWER)
- `search` - Search by name or description
- `ordering` - Order by field (-created_at)

**Create Team Request Body:**
```json
{
  "name": "Development Team",
  "description": "Backend development team",
  "organization_id": "org-uuid"
}
```

**Create Team Response (201):**
```json
{
  "message": "Team created successfully",
  "data": {
    "id": "team-uuid",
    "name": "Development Team",
    "description": "Backend development team",
    "organization": "org-uuid",
    "created_by": "user-uuid",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Team Roles:**
- `OWNER` - Manages team, invites members
- `MANAGER` - Can manage team workflows
- `LEAD` - Can assign tasks, manage workflows
- `MEMBER` - Normal team member
- `VIEWER` - Read-only access

---

## 📊 Projects

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/projects/get-user-projects/` | List all projects user is member of (paginated) |
| POST | `/projects/create-project/` | Create a new project |
| GET  | `/projects/get-project-details/` | Get project details |
| PUT  | `/projects/update-project/` | Update project details |
| DELETE | `/projects/delete-project/` | Delete project (owner only) |
| GET  | `/projects/get_org-projects/` | List all projects in an organization |
| GET  | `/projects/get-team-projects/` | List all projects in a team |
| GET  | `/projects/get-project-members/` | List all project members |
| POST | `/projects/send-invite/` | Send invite to user for project |
| POST | `/projects/accept-project-invite/` | Accept project invite |
| PUT  | `/projects/update-member/` | Update member role in project |
| DELETE | `/projects/remove-member/` | Remove member from project |
| DELETE | `/projects/self-remove-member/` | Remove yourself from project |
| PUT  | `/projects/transfer-owner/` | Transfer project ownership |

**Query Parameters:**
- `project_id` - Project ID (required for most operations)
- `org_id` - Organization ID (for org_projects endpoint)
- `team_id` - Team ID (for team_projects endpoint)
- `email` - User email (for member operations)
- `role` - Role to assign (OWNER, MANAGER, LEAD, CONTRIBUTOR, VIEWER)
- `search` - Search by name or description
- `ordering` - Order by field (-created_at)

**Create Project Request Body:**
```json
{
  "name": "My Project",
  "description": "Project description",
  "organization_id": "org-uuid",
  "team_id": "team-uuid",
  "status": "PLANNING"
}
```

**Create Project Response (201):**
```json
{
  "message": "Project created successfully",
  "data": {
    "id": "project-uuid",
    "name": "My Project",
    "description": "Project description",
    "organization": "org-uuid",
    "team": "team-uuid",
    "created_by": "user-uuid",
    "status": "PLANNING",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Project Roles:**
- `OWNER` - Full control of project
- `MANAGER` - Can manage tasks and members
- `LEAD` - Can assign tasks and manage workflows
- `CONTRIBUTOR` - Can work on tasks
- `VIEWER` - Can view everything

**Project Status Values:**
- `PLANNING` - Project in planning phase
- `ACTIVE` - Project is currently active
- `COMPLETED` - Project has been completed
- `ON_HOLD` - Project is on hold
- `ARCHIVED` - Project has been archived

---

## 📋 Tasks

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/tasks/get-project-tasks/` | List all tasks in a project (paginated) |
| GET  | `/tasks/get-my-tasks/` | List tasks assigned to the current user across all projects |
| POST | `/tasks/create-task/` | Create a new task |
| GET  | `/tasks/get_task_details/` | Get task details |
| PUT  | `/tasks/update-task/` | Update task details |
| DELETE | `/tasks/delete-task/` | Delete task (creator/manager only) |

**Query Parameters:**
- `project_id` - Project ID (required for `get-project-tasks/`)
- `status` - Filter by status (TO_DO, IN_PROGRESS, REVIEW, DONE, BLOCKED)
- `priority` - Filter by priority (LOW, MEDIUM, HIGH, URGENT)
- `task_type` - Filter by type (BUG, FEATURE, IMPROVEMENT, DOCUMENTATION)
- `assigned_to` - Filter by assignee UUID
- `parent_id` - Filter by parent task UUID (for subtasks)
- `search` - Search in title and description
- `ordering` - Order by field (-created_at, due_date, priority)

**Create Task Request Body:**
```json
{
  "project_id": "project-uuid",
  "title": "Task Title",
  "description": "Task description",
  "start_date": "2024-01-15",
  "due_date": "2024-01-20",
  "status": "TO_DO",
  "priority": "HIGH",
  "task_type": "FEATURE",
  "assigned_to": "user-uuid",
  "parent_id": null
}
```

**Create Task Response (201):**
```json
{
  "message": "Task created successfully",
  "data": {
    "id": "task-uuid",
    "project": "project-uuid",
    "parent": null,
    "title": "Task Title",
    "description": "Task description",
    "start_date": "2024-01-15",
    "due_date": "2024-01-20",
    "status": "TO_DO",
    "priority": "HIGH",
    "task_type": "FEATURE",
    "assigned_to": "user-uuid",
    "created_by": "user-uuid",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Task Status Values:**
- `TO_DO` - Not started
- `IN_PROGRESS` - Currently being worked on
- `REVIEW` - Waiting for review
- `DONE` - Completed
- `BLOCKED` - Blocked by dependencies

**Task Priority Values:**
- `LOW` - Low priority
- `MEDIUM` - Medium priority
- `HIGH` - High priority
- `URGENT` - Urgent/Critical

**Task Type Values:**
- `BUG` - Bug fix
- `FEATURE` - New feature
- `IMPROVEMENT` - Improvement
- `DOCUMENTATION` - Documentation

---

## ⚙️ Governance Settings

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/governance/get-org-settings/` | Get organization settings |
| GET  | `/governance/get-team-settings/` | Get team settings |
| GET  | `/governance/get-project-settings/` | Get project settings |
| PUT  | `/governance/update-org-settings/` | Update organization settings |
| PUT  | `/governance/update-team-settings/` | Update team settings |
| PUT  | `/governance/update-project-settings/` | Update project settings |

**Query Parameters:**
- `org_id` - Organization ID (for org settings)
- `team_id` - Team ID (for team settings)
- `project_id` - Project ID (for project settings)

**Organization Settings Response:**
```json
{
  "id": "settings-uuid",
  "organization": "org-uuid",
  "allow_team_creation": true,
  "allow_project_creation": true,
  "allow_member_invites": true,
  "allow_member_updates": true,
  "allow_member_removal": true,
  "allow_self_removal": true,
  "create_team_min_role": "MANAGER",
  "create_project_min_role": "MANAGER",
  "invite_member_min_role": "ADMIN",
  "update_member_min_role": "ADMIN",
  "remove_member_min_role": "ADMIN",
  "default_member_role": "MEMBER"
}
```

**Team Settings Response:**
```json
{
  "id": "settings-uuid",
  "team": "team-uuid",
  "allow_project_creation": true,
  "allow_member_invites": true,
  "allow_member_updates": true,
  "allow_member_removal": true,
  "allow_self_removal": true,
  "create_project_min_role": "MANAGER",
  "invite_member_min_role": "MANAGER",
  "update_member_min_role": "MANAGER",
  "remove_member_min_role": "MANAGER",
  "default_member_role": "MEMBER"
}
```

**Project Settings Response:**
```json
{
  "id": "settings-uuid",
  "project": "project-uuid",
  "allow_task_creation": true,
  "allow_task_updates": true,
  "allow_task_deletions": true,
  "allow_member_invites": true,
  "allow_member_updates": true,
  "allow_member_removal": true,
  "allow_self_removal": true,
  "create_task_min_role": "CONTRIBUTOR",
  "update_task_min_role": "CONTRIBUTOR",
  "delete_task_min_role": "MANAGER",
  "invite_member_min_role": "MANAGER",
  "update_member_min_role": "MANAGER",
  "remove_member_min_role": "MANAGER",
  "default_member_role": "CONTRIBUTOR"
}
```

---

## 📊 Activity Logs

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/activity-logs/` | List activity logs (user's own or all for admins) |
| GET  | `/activity-logs/{id}/` | Get specific activity log |
| GET  | `/activity-logs/my_activities/` | Get current user's recent activities |
| GET  | `/activity-logs/stats/` | Get activity statistics |

**Query Parameters:**
- `action` - Filter by action (CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, ACCESS, FAILED)
- `resource_type` - Filter by resource type (Organization, Project, Team, Task, User, etc.)
- `method` - Filter by HTTP method (GET, POST, PUT, PATCH, DELETE)
- `status_code` - Filter by HTTP status code
- `status_code_gte` - Filter by status code >= value
- `status_code_lte` - Filter by status code <= value
- `timestamp_after` - Filter activities after date
- `timestamp_before` - Filter activities before date
- `username` - Search by username (admin only)
- `search` - Full-text search
- `ordering` - Order by field (-timestamp, response_time_ms, status_code)
- `page` - Page number for pagination

**Activity Log Response Example (List):**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/activity-logs/?page=2",
  "previous": null,
  "results": [
    {
      "id": "log-uuid",
      "user_email": "user@example.com",
      "username": "user@example.com",
      "action": "CREATE",
      "resource_type": "Project",
      "resource_name": "My Project",
      "description": "CREATE Project: My Project",
      "method": "POST",
      "path": "/api/v1/projects/create-project/",
      "status_code": 201,
      "response_time_ms": 145.23,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Activity Log Response Example (Stats):**
```json
{
  "message": "Success",
  "data": {
    "total_activities": 1250,
    "by_action": {
      "CREATE": 350,
      "READ": 600,
      "UPDATE": 200,
      "DELETE": 50,
      "LOGIN": 50
    },
    "by_resource": {
      "Project": 400,
      "Task": 600,
      "Organization": 150,
      "Team": 100
    },
    "by_status": {
      "success_2xx": 1200,
      "redirect_3xx": 10,
      "client_error_4xx": 30,
      "server_error_5xx": 10
    }
  }
}
```

---

## 🧠 Important Notes

- All endpoints require JWT token authentication (except register, login, and password reset)
- Admin users have elevated access across organizations and projects
- Pagination and filtering supported via DRF defaults
- Activity logs are automatically tracked for all API requests
- Sensitive data (passwords, tokens) is automatically redacted from logs
- Soft delete is implemented for Users, Organizations, Teams, Projects, and Tasks
- Deleted entities are never returned in API responses
- All list endpoints automatically filter out deleted entities using `is_deleted=False`
- See [Activity Tracking Documentation](ACTIVITY_TRACKING.md) for detailed activity log information
- See [Authentication Flow](AUTHENTICATION_FLOW.md) for detailed authentication and authorization flow
