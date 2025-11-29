"""
Theme scheduling based on solar position.

TEAM_003: REQ-SCHED-002, REQ-SCHED-003, REQ-SCHED-004

Provides automatic SFW/NSFW theme switching based on:
- Solar position (sunrise/sunset)
- Manual time overrides
- Probability blending during transitions
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, date
from typing import Optional, List, Tuple

from astral import LocationInfo
from astral.sun import sun

from .exceptions import ConfigError

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """
    Configuration for theme scheduling.
    
    TEAM_003: REQ-SCHED-002 - Solar-based scheduling with manual override.
    """
    # Location for solar calculations
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Theme names
    day_theme: str = "default"
    night_theme: str = "nsfw"
    
    # Manual time overrides (take priority over solar)
    nsfw_start: Optional[str] = None  # "HH:MM" format
    nsfw_end: Optional[str] = None    # "HH:MM" format
    
    # Blend settings (REQ-SCHED-003)
    blend_duration_minutes: int = 30
    
    # Timezone (None = system local)
    timezone: Optional[str] = None
    
    def has_location(self) -> bool:
        """Check if location is configured for solar calculations."""
        return self.latitude is not None and self.longitude is not None
    
    def has_manual_times(self) -> bool:
        """Check if manual times are configured."""
        return self.nsfw_start is not None and self.nsfw_end is not None
    
    def get_nsfw_start_time(self) -> Optional[time]:
        """Parse nsfw_start as time object."""
        if self.nsfw_start:
            return datetime.strptime(self.nsfw_start, "%H:%M").time()
        return None
    
    def get_nsfw_end_time(self) -> Optional[time]:
        """Parse nsfw_end as time object."""
        if self.nsfw_end:
            return datetime.strptime(self.nsfw_end, "%H:%M").time()
        return None


@dataclass
class ThemeResult:
    """
    Result of theme determination.
    
    TEAM_003: REQ-SCHED-003 - Includes probability for blend transitions.
    """
    theme: str
    probability: float = 1.0  # 0.0 to 1.0
    is_blend_period: bool = False
    next_transition: Optional[datetime] = None
    sunset_time: Optional[time] = None
    sunrise_time: Optional[time] = None


@dataclass
class ScheduleEntry:
    """Entry in the 24-hour schedule table."""
    time: time
    theme: str
    probability: float = 1.0
    is_transition: bool = False


class ThemeScheduler:
    """
    Determines current theme based on time and solar position.
    
    TEAM_003: REQ-SCHED-002, REQ-SCHED-003
    """
    
    def __init__(self, config: ScheduleConfig) -> None:
        self.config = config
        self._location: Optional[LocationInfo] = None
        
        if config.has_location():
            self._location = LocationInfo(
                name="User Location",
                region="",
                timezone=config.timezone or "local",
                latitude=config.latitude,
                longitude=config.longitude,
            )
    
    def get_sun_times(self, for_date: Optional[date] = None) -> Tuple[Optional[time], Optional[time]]:
        """
        Get sunrise and sunset times for a date.
        
        Args:
            for_date: Date to calculate for (default: today)
            
        Returns:
            Tuple of (sunrise_time, sunset_time), or (None, None) if no location
        """
        if not self._location:
            return None, None
        
        if for_date is None:
            for_date = date.today()
        
        try:
            s = sun(self._location.observer, date=for_date)
            sunrise = s["sunrise"].time()
            sunset = s["sunset"].time()
            logger.debug(f"Solar times for {for_date}: sunrise={sunrise}, sunset={sunset}")
            return sunrise, sunset
        except Exception as e:
            logger.error(f"Failed to calculate solar times: {e}")
            raise ConfigError(f"Solar calculation failed: {e}")
    
    def _is_night_time(self, current: time, night_start: time, night_end: time) -> bool:
        """
        Check if current time is in night period.
        
        Handles wrap-around midnight (e.g., 22:00 to 06:00).
        """
        if night_start < night_end:
            # Simple case: start and end on same day
            return night_start <= current < night_end
        else:
            # Wraps midnight: e.g., 22:00 to 06:00
            return current >= night_start or current < night_end
    
    def _calculate_blend_probability(
        self,
        current: time,
        transition_time: time,
        blend_minutes: int,
        is_sunset: bool = True,
    ) -> Tuple[float, float]:
        """
        Calculate SFW/NSFW probability during blend period.
        
        REQ-SCHED-003: Linear interpolation during blend window.
        
        Args:
            current: Current time
            transition_time: Sunset or sunrise time
            blend_minutes: Duration of blend period
            is_sunset: True for sunset (SFW->NSFW), False for sunrise (NSFW->SFW)
            
        Returns:
            Tuple of (sfw_probability, nsfw_probability) as 0.0-1.0
        """
        # Convert to minutes from midnight
        current_mins = current.hour * 60 + current.minute
        transition_mins = transition_time.hour * 60 + transition_time.minute
        
        # Distance from transition in minutes
        distance = current_mins - transition_mins
        
        # Handle midnight wrap-around
        if distance > 720:  # More than 12 hours ahead
            distance -= 1440
        elif distance < -720:  # More than 12 hours behind
            distance += 1440
        
        # blend_minutes is the duration on EACH side of the transition
        # Total blend window is 2 * blend_minutes
        if is_sunset:
            # Sunset: SFW -> NSFW
            # Blend window: -blend_minutes to +blend_minutes centered on transition
            # At -blend_minutes: 100% SFW, at 0: 50/50, at +blend_minutes: 0% SFW
            if distance < -blend_minutes:
                return 1.0, 0.0  # Before blend: 100% SFW
            elif distance > blend_minutes:
                return 0.0, 1.0  # After blend: 100% NSFW
            else:
                # Linear interpolation centered on transition
                # At -blend_minutes: 100% SFW, at 0: 50/50, at +blend_minutes: 0% SFW
                nsfw_prob = (distance + blend_minutes) / (2 * blend_minutes)
                return 1.0 - nsfw_prob, nsfw_prob
        else:
            # Sunrise: NSFW -> SFW
            if distance < -blend_minutes:
                return 0.0, 1.0  # Before blend: 100% NSFW
            elif distance > blend_minutes:
                return 1.0, 0.0  # After blend: 100% SFW
            else:
                # Linear interpolation
                sfw_prob = (distance + blend_minutes) / (2 * blend_minutes)
                return sfw_prob, 1.0 - sfw_prob
    
    def get_current_theme(
        self,
        current_time: Optional[datetime] = None,
        include_probability: bool = True,
    ) -> ThemeResult:
        """
        Determine the current theme based on time.
        
        REQ-SCHED-002: Solar-based with manual override.
        REQ-SCHED-003: Probability blend during transitions.
        
        Args:
            current_time: Time to check (default: now)
            include_probability: Whether to calculate blend probability
            
        Returns:
            ThemeResult with theme name and probability
        """
        if current_time is None:
            current_time = datetime.now()
        
        current = current_time.time()
        
        # Get transition times
        if self.config.has_manual_times():
            # Manual times take priority (REQ-SCHED-002)
            night_start = self.config.get_nsfw_start_time()
            night_end = self.config.get_nsfw_end_time()
            sunrise_time = night_end
            sunset_time = night_start
            logger.debug(f"Using manual times: {night_start} to {night_end}")
        elif self._location:
            # Solar-based
            sunrise_time, sunset_time = self.get_sun_times(current_time.date())
            night_start = sunset_time
            night_end = sunrise_time
            logger.debug(f"Using solar times: sunset={sunset_time}, sunrise={sunrise_time}")
        else:
            # No scheduling configured - use day theme
            logger.warning("No schedule configured, using day theme")
            return ThemeResult(
                theme=self.config.day_theme,
                probability=1.0,
            )
        
        # Determine if we're in night period
        is_night = self._is_night_time(current, night_start, night_end)
        
        # Calculate probability if in blend period
        sfw_prob = 1.0 if not is_night else 0.0
        nsfw_prob = 0.0 if not is_night else 1.0
        is_blend = False
        
        if include_probability and self.config.blend_duration_minutes > 0:
            blend_mins = self.config.blend_duration_minutes
            
            # Check if near sunset
            sunset_sfw, sunset_nsfw = self._calculate_blend_probability(
                current, night_start, blend_mins, is_sunset=True
            )
            
            # Check if near sunrise
            sunrise_sfw, sunrise_nsfw = self._calculate_blend_probability(
                current, night_end, blend_mins, is_sunset=False
            )
            
            # Use the probability that indicates we're in a blend period
            if 0 < sunset_nsfw < 1:
                sfw_prob, nsfw_prob = sunset_sfw, sunset_nsfw
                is_blend = True
            elif 0 < sunrise_sfw < 1:
                sfw_prob, nsfw_prob = sunrise_sfw, sunrise_nsfw
                is_blend = True
        
        # Determine theme based on probability
        if is_blend:
            # During blend, use the higher probability theme
            if nsfw_prob > sfw_prob:
                theme = self.config.night_theme
                probability = nsfw_prob
            else:
                theme = self.config.day_theme
                probability = sfw_prob
        else:
            theme = self.config.night_theme if is_night else self.config.day_theme
            probability = 1.0
        
        return ThemeResult(
            theme=theme,
            probability=probability,
            is_blend_period=is_blend,
            sunset_time=sunset_time,
            sunrise_time=sunrise_time,
        )
    
    def get_theme_probability(
        self,
        current_time: Optional[datetime] = None,
    ) -> Tuple[float, float]:
        """
        Get SFW/NSFW probability at current time.
        
        REQ-SCHED-003: For blend period calculations.
        
        Returns:
            Tuple of (sfw_probability, nsfw_probability) as percentages (0-100)
        """
        if current_time is None:
            current_time = datetime.now()
        
        current = current_time.time()
        
        # Get transition times
        if self.config.has_manual_times():
            night_start = self.config.get_nsfw_start_time()
            night_end = self.config.get_nsfw_end_time()
        elif self._location:
            _, sunset_time = self.get_sun_times(current_time.date())
            sunrise_time, _ = self.get_sun_times(current_time.date())
            night_start = sunset_time
            night_end = sunrise_time
        else:
            return 100.0, 0.0  # Default to SFW
        
        blend_mins = self.config.blend_duration_minutes
        
        # Calculate sunset blend
        sfw_prob, nsfw_prob = self._calculate_blend_probability(
            current, night_start, blend_mins, is_sunset=True
        )
        
        # Convert to percentages
        return sfw_prob * 100, nsfw_prob * 100
    
    def get_24h_schedule(
        self,
        for_date: Optional[date] = None,
        interval_minutes: int = 60,
    ) -> List[ScheduleEntry]:
        """
        Generate 24-hour schedule table.
        
        REQ-SCHED-004: For status display.
        
        Args:
            for_date: Date to generate schedule for
            interval_minutes: Interval between entries
            
        Returns:
            List of ScheduleEntry for each time slot
        """
        if for_date is None:
            for_date = date.today()
        
        entries = []
        
        for hour in range(24):
            for minute in range(0, 60, interval_minutes):
                t = time(hour, minute)
                dt = datetime.combine(for_date, t)
                
                result = self.get_current_theme(dt, include_probability=True)
                
                entries.append(ScheduleEntry(
                    time=t,
                    theme=result.theme,
                    probability=result.probability,
                    is_transition=result.is_blend_period,
                ))
        
        return entries
    
    def format_schedule_table(self, entries: Optional[List[ScheduleEntry]] = None) -> str:
        """
        Format schedule as human-readable table.
        
        REQ-SCHED-004: For `darkwall status` output.
        """
        if entries is None:
            entries = self.get_24h_schedule()
        
        lines = [
            "Theme Schedule (next 24h):",
            "TIME        THEME       PROBABILITY",
            "-" * 40,
        ]
        
        for entry in entries:
            time_str = entry.time.strftime("%H:%M")
            prob_str = f"{entry.probability * 100:.0f}%"
            
            if entry.is_transition:
                theme_str = f"({entry.theme})"
            else:
                theme_str = entry.theme
            
            lines.append(f"{time_str}       {theme_str:<12}{prob_str}")
        
        return "\n".join(lines)
    
    def to_json(self) -> dict:
        """
        Export schedule state as JSON for waybar integration.
        
        REQ-MISC-003: JSON output for external tools.
        """
        result = self.get_current_theme()
        
        return {
            "current_theme": result.theme,
            "probability": result.probability,
            "is_blend_period": result.is_blend_period,
            "sunset_time": result.sunset_time.strftime("%H:%M") if result.sunset_time else None,
            "sunrise_time": result.sunrise_time.strftime("%H:%M") if result.sunrise_time else None,
            "next_transition": result.next_transition.isoformat() if result.next_transition else None,
            "day_theme": self.config.day_theme,
            "night_theme": self.config.night_theme,
        }
