## ADDED Requirements

### Requirement: Admin dashboard shows open query count
The `/admin` page SHALL display a count of currently open queries (status = PENDING or ASSIGNED), computed from the database at render time.

#### Scenario: Open count reflects database state
- **WHEN** there are 3 PENDING queries and 2 ASSIGNED queries in the database
- **THEN** the admin dashboard displays "5" as the open query count

#### Scenario: Resolved queries excluded from open count
- **WHEN** there are 3 PENDING queries and 4 RESOLVED queries in the database
- **THEN** the admin dashboard displays "3" as the open query count (not 7)

#### Scenario: Open count is zero
- **WHEN** there are no PENDING or ASSIGNED queries in the database
- **THEN** the admin dashboard displays "0" as the open query count

### Requirement: Admin dashboard shows resolved query count
The `/admin` page SHALL display a count of resolved queries (status = RESOLVED), computed from the database at render time.

#### Scenario: Resolved count reflects database state
- **WHEN** there are 7 RESOLVED queries in the database
- **THEN** the admin dashboard displays "7" as the resolved query count

#### Scenario: Resolved count is zero
- **WHEN** there are no RESOLVED queries in the database
- **THEN** the admin dashboard displays "0" as the resolved query count

### Requirement: Admin dashboard shows mentor workload summary
The `/admin` page SHALL display a mentor workload summary showing the number of active mentors out of total mentors and the sum of current loads across all mentors.

#### Scenario: Workload summary with active and inactive mentors
- **WHEN** there are 3 mentors total, 2 active, with combined current_load of 5
- **THEN** the admin dashboard displays "2/3 active" (or equivalent) and a total load of 5

#### Scenario: Workload summary with no active mentors
- **WHEN** there are 2 mentors total, 0 active
- **THEN** the admin dashboard displays "0/2 active" and a total load of 0
