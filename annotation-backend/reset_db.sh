#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Resetting Database ===${NC}"

# Create data directory if it doesn't exist
mkdir -p data

# Remove existing database
echo -e "${BLUE}Removing existing database...${NC}"
rm -f data/app.db
echo -e "${GREEN}✓ Database file removed${NC}"

# Run alembic migrations
echo -e "${BLUE}Running database migrations...${NC}"
alembic upgrade head
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database migrations completed successfully${NC}"
else
    echo -e "${RED}✗ Failed to run database migrations${NC}"
    exit 1
fi

# Create admin user using Python script
echo -e "${BLUE}Creating admin user...${NC}"
python3 - << EOF
from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash

# Create admin user
db = SessionLocal()
try:
    admin = User(
        username="admin",
        hashed_password=get_password_hash("admin"),
        is_admin=True
    )
    db.add(admin)
    db.commit()
    print("✓ Admin user created successfully")
except Exception as e:
    print(f"✗ Failed to create admin user: {str(e)}")
    db.rollback()
finally:
    db.close()
EOF

echo -e "${GREEN}✓ Database reset completed successfully!${NC}" 
