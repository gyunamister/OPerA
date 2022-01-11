from enum import Enum


# TODO still not great as hashing is broken by default
class ValueSetEnum(Enum):
    vals: set

    def __new__(cls, value):
        obj = object.__new__(cls)
        obj._value_ = value
        if not hasattr(cls, 'vals'):
            cls.vals = set()
        cls.vals.add(value)
        return obj

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and self.value == o.value


class ActivityProperty(ValueSetEnum):
    QueueingDiscipline = 'queueing_discipline'
    ProcessingTimeSampler = 'processing_time_sampler'
    DelaySampler = 'delay_sampler'
    ObjectType = 'object_type'


class ActivityState(ValueSetEnum):
    InBusiness = 'in_business'
    QueueLength = 'queue_length'


class ResourceProperty(ValueSetEnum):
    Capacity = 'capacity'
    Performance = 'performance'
    Cooldown = 'cooldown'


class ResourceState(ValueSetEnum):
    InBusiness = 'in_business'
    CurrentlyAssigned = 'currently_assigned'
    OnCooldown = 'on_cooldown'
    Disabled = 'disabled'


class Lifecycle(ValueSetEnum):
    Enabled = 'enabled'
    Scheduled = 'scheduled'
    Started = 'started'
    Completed = 'completed'


class AvailableLifecycles(Enum):
    CompleteOnly = {'complete'}
    StartOnly = {'start'}
    StartComplete = {'start', 'complete'}
    ScheduleStartComplete = {'schedule', 'start', 'complete'}

    def __new__(cls, *args, **kwargs):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, included_lifecycles):
        self.vals = included_lifecycles

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and self.value == o.value


class ExecutionParameters(Enum):
    CasesToGenerate = 'cases'
    GenerationCutoffDate = 'creation_cutoff'
    SimStartDate = 'sim_start'
    SimCutoffDate = 'sim_cutoff'
    RealtimeLimit = 'realtime_limit'
    Pause = 'pause'
