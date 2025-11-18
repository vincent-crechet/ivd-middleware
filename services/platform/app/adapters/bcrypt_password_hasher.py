"""Bcrypt implementation of password hasher."""

import bcrypt

from app.ports import IPasswordHasher


class BcryptPasswordHasher(IPasswordHasher):
    """Bcrypt implementation for secure password hashing."""

    def hash(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    def verify(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against a bcrypt hash.

        Args:
            password: Plain text password to verify
            hashed_password: Previously hashed password

        Returns:
            True if password matches, False otherwise
        """
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
