"""Password hasher port."""

import abc


class IPasswordHasher(abc.ABC):
    """
    Port: Abstract contract for password hashing operations.

    Implementations provide secure password hashing using algorithms like bcrypt.
    """

    @abc.abstractmethod
    def hash(self, password: str) -> str:
        """
        Hash a plain text password.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        pass

    @abc.abstractmethod
    def verify(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            password: Plain text password to verify
            hashed_password: Previously hashed password

        Returns:
            True if password matches, False otherwise
        """
        pass
