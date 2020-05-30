# Shepherd
*The next generation course building CI tool for A+*

## Architecture

Keep updating...

![architecture](./assets/image/arch.png)

## Project Formation

### Auth

* Get access to Shepherd from A+ using Oauth. ( Get `signal` from `flask-lti-login` and authenticate user).
* [model](apluslms_shepherd/auth/models.py): User

### Groups
* Group users, grant user different privileges and permissions according to the group.
* Tree-like structure. Example: Aalto &rarr; CSI &rarr; CS &rarr; Programming_1.
* [model](apluslms_shepherd/groups/models.py):
    - Group: many-to-many relationship with User.
    - GroupPermission: the permission types of Group. Currently two types: `(create) subgroups`, `(create) courses`.
    - CreateGroupPerm: the permission of groups for creating (sub)groups. 
                       field `group` is the group with the `(create) subgroups` permission; 
                       field `target_group` is the group which `group` can create subgroups under.
    - CreateCoursePerm: the permission of groups for creating courses. the field `pattern` defines the prefix that the course key should follow. 
    - ManageCoursePerm: the permission for managing courses. The owner roles of a course include `admin` and `assistant`.

### Courses
* Course management interface
* To create new courses, the user needs to be in a group with the `(create) courses` permission.
* [model](apluslms_shepherd/courses/models.py): CourseInstance

### Build
* Record the build processes of courses
* [model](apluslms_shepherd/build/models.py): Build, BuildLog

#### Repos
* SSH key management
* [model](apluslms_shepherd/repos/models.py): GitRepository

### Webhooks
Handle push webhook in `GitHub` or `Gitlab`.

### Celery Tasks

* [build](apluslms_shepherd/build/tasks/tasks.py)
    
    Define Build tasks, define automated pipeline (pull/clone->build->deploy->clean).
    
* [repos - deploy key](apluslms_shepherd/repos/tasks/tasks.py)
    * Define background task for deploy key pair generation.
    * Define the scheduled task for key validation.

### Message Broker
Message broker for updating frontend statues display in realtime, and also routing realtime log output to frontend.
