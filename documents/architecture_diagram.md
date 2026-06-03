
---
config:
  theme: redux
  layout: fixed
---
```mermaid
flowchart TB
 subgraph s1["Business Logic"]
        n4["Project Service"]
        n8["Document Service"]
  end
 subgraph s2["Data Access Layer"]
        n12["S3 Controller"]
        n13["PostgreSQL Controller"]
  end
    n1(["User"]) --> n2["API Gateway Layer"]
    n2 --> n3["Auth Layer"]
    s1 --> s2
    s2 --> n7["S3 Storage"] & n5["PostgreSQL"]
    n3 --> s1

    n4@{ shape: proc}
    n8@{ shape: proc}
    n11@{ shape: proc}
    n12@{ shape: proc}
    n13@{ shape: proc}
    n2@{ shape: proc}
    n3@{ shape: proc}
    n6@{ shape: db}
    n7@{ shape: db}
    n5@{ shape: db}
     n4:::businessLogic
     n8:::businessLogic
     n11:::dataAccess
     n12:::dataAccess
     n13:::dataAccess
     n2:::gateway
     n3:::gateway
     n6:::storage
     n7:::storage
     n5:::storage
```