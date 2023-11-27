from datetime import timedelta

from django.db import models
from django.core.exceptions import ValidationError


# Create your models here.

class BaseCharacter(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        abstract = True


class Mage(BaseCharacter):
    elemental_power = models.CharField(max_length=100)
    spellbook_type = models.CharField(max_length=100)


class Assassin(BaseCharacter):
    weapon_type = models.CharField(max_length=100)
    assassination_technique = models.CharField(max_length=100)


class DemonHunter(BaseCharacter):
    weapon_type = models.CharField(max_length=100)
    demon_slaying_ability = models.CharField(max_length=100)


class TimeMage(Mage):
    time_magic_mastery = models.CharField(max_length=100)
    temporal_shift_ability = models.CharField(max_length=100)


class Necromancer(Mage):
    raise_dead_ability = models.CharField(max_length=100)


class ViperAssassin(Assassin):
    venomous_strikes_mastery = models.CharField(max_length=100)
    venomous_bite_ability = models.CharField(max_length=100)


class ShadowbladeAssassin(Assassin):
    shadowstep_ability = models.CharField(max_length=100)


class VengeanceDemonHunter(DemonHunter):
    vengeance_mastery = models.CharField(max_length=100)
    retribution_ability = models.CharField(max_length=100)


class FelbladeDemonHunter(DemonHunter):
    felblade_ability = models.CharField(max_length=100)


class UserProfile(models.Model):
    username = models.CharField(max_length=70, unique=True)
    email = models.EmailField(unique=True)
    bio = models.TextField(null=True, blank=True)


class Message(models.Model):
    sender = models.ForeignKey(to=UserProfile, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(to=UserProfile, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def mark_as_read(self) -> None:
        self.is_read = True

    def mark_as_unread(self) -> None:
        self.is_read = False

    def reply_to_message(self, reply_content: str, receiver: UserProfile):
        return Message(
            sender=self.receiver,
            receiver=receiver,
            content=reply_content
        )

    def forward_message(self, sender, receiver) -> object:
        return Message(
            sender=sender,
            receiver=receiver,
            content=self.content
        )


class StudentIDField(models.PositiveIntegerField):
    # Not necessary to use init if we don't change attributes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value) -> int:
        return int(value)


class Student(models.Model):
    name = models.CharField(max_length=100)
    student_id = StudentIDField()


class MaskedCreditCardField(models.CharField):
    def __init__(self, *args, **kwargs):
        # The user is unable to change that when instantiating the field
        kwargs["max_length"] = 20
        super().__init__(*args, **kwargs)

    def to_python(self, value) -> str:
        """We use to_python instead of get_prep_value because
        get_prep_value calls to_python (1 redundant function call)"""

        if not isinstance(value, str):
            raise ValidationError('The card number must be a string')
        if not value.isnumeric():
            raise ValidationError('The card number must contain only digits')
        if len(value) != 16:
            raise ValidationError('The card number must be exactly 16 characters long')

        return f'****-****-****-{value[-4:]}'


class CreditCard(models.Model):
    card_owner = models.CharField(max_length=100)
    card_number = MaskedCreditCardField(max_length=20)


class Hotel(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)


class Room(models.Model):
    hotel = models.ForeignKey(to=Hotel, on_delete=models.CASCADE)
    number = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField()
    total_guests = models.PositiveIntegerField()
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)

    # We can write everything in save, but it's better to split it
    def clean(self) -> None:
        if self.total_guests > self.capacity:
            raise ValidationError('Total guests are more than the capacity of the room')

    def save(self, *args, **kwargs) -> str:
        self.clean()  # Means validation
        super().save(*args, **kwargs)
        return f"Room {self.number} created successfully"


class BaseReservation(models.Model):
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()

    def reservation_period(self) -> int:
        # Same as "self.end_date.day - self.start_date.day"
        return (self.end_date - self.start_date).days

    def calculate_total_cost(self) -> float:
        reservation_period: int = self.end_date.day - self.start_date.day
        total_price = reservation_period * float(self.room.price_per_night)

        return round(total_price, 1)

    @property
    def is_available(self) -> bool:
        reservations = self.__class__.objects.filter(
            room=self.room,
            end_date__gte=self.start_date,
            start_date__lte=self.end_date,
        )
        return not reservations.exists()

    def clean(self) -> None:
        if self.start_date >= self.end_date:
            raise ValidationError('Start date cannot be after or in the same end date')
        if not self.is_available:
            raise ValidationError(f'Room {self.room.number} cannot be reserved')

    class Meta:
        abstract = True


class RegularReservation(BaseReservation):
    def save(self, *args, **kwargs) -> str:
        super().clean()
        super().save(*args, **kwargs)
        return f'Regular reservation for room {self.room.number}'


class SpecialReservation(BaseReservation):
    def save(self, *args, **kwargs) -> str:
        super().clean()
        return f'Regular reservation for room {self.room.number}'

    def extend_reservation(self, days: int) -> str:
        reservations = SpecialReservation.__class__.objects.filter(
            room=self.room,
            end_date__gte=self.start_date,
            start_date__lte=self.end_date + timedelta(days=days),
        )

        if not reservations:
            raise ValidationError('Error during extending reservation')

        self.end_date += timedelta(days=days)
        self.save()

        return f"Extended reservation for room {self.room.number} with {days} days"