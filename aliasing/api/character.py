from functools import cached_property
from dataclasses import asdict

import cogs5e.models.sheet.player as player_api
from aliasing import helpers
from aliasing.api.statblock import AliasStatBlock
from cogs5e.models.errors import ConsumableException
from cogs5e.utils.gameutils import parse_coin_args


class AliasCharacter(AliasStatBlock):
    def __init__(self, character, interpreter=None):
        """
        :type character: cogs5e.models.character.Character
        :type interpreter: draconic.DraconicInterpreter
        """
        super().__init__(character)
        self._character = character
        self._interpreter = interpreter
        self._coinpurse = None

    # helpers
    def _get_consumable(self, name):
        name = str(name)
        consumable = self._character.get_consumable(name)
        if consumable is None:
            raise ConsumableException(f"There is no counter named {name}.")
        return consumable

    # methods
    # --- ccs ---
    @cached_property
    def consumables(self):
        """
        Returns a list of custom counters on the character.

        :rtype: list[AliasCustomCounter]
        """
        return [AliasCustomCounter(cc) for cc in self._character.consumables]

    def cc(self, name):
        """
        Gets the AliasCustomCounter with the name `name`

        :param str name: The name of the custom counter to get.
        :returns: The custom counter.
        :rtype: AliasCustomCounter
        :raises: :exc:`ConsumableException` if the counter does not exist.
        """
        return AliasCustomCounter(self._get_consumable(name))

    def get_cc(self, name):
        """
        Gets the value of a custom counter.

        :param str name: The name of the custom counter to get.
        :returns: The current value of the counter.
        :rtype: int
        :raises: :exc:`ConsumableException` if the counter does not exist.
        """
        return self._get_consumable(name).value

    def get_cc_max(self, name):
        """
        Gets the maximum value of a custom counter.

        :param str name: The name of the custom counter maximum to get.
        :returns: The maximum value of the counter. If a counter has no maximum, it will return INT_MAX (2^31-1).
        :rtype: int
        :raises: :exc:`ConsumableException` if the counter does not exist.
        """
        return self._get_consumable(name).get_max()

    def get_cc_min(self, name):
        """
        Gets the minimum value of a custom counter.

        :param str name: The name of the custom counter minimum to get.
        :returns: The minimum value of the counter. If a counter has no minimum, it will return INT_MIN (-2^31).
        :rtype: int
        :raises: :exc:`ConsumableException` if the counter does not exist.
        """
        return self._get_consumable(name).get_min()

    def set_cc(self, name, value: int, strict=False):
        """
        Sets the value of a custom counter.

        :param str name: The name of the custom counter to set.
        :param int value: The value to set the counter to.
        :param bool strict: If ``True``, will raise a :exc:`CounterOutOfBounds` if the new value is out of bounds, otherwise silently clips to bounds.
        :raises: :exc:`ConsumableException` if the counter does not exist.
        :returns: The cc's new value.
        :rtype: int
        """
        return self._get_consumable(name).set(int(value), strict)

    def mod_cc(self, name, val: int, strict=False):
        """
        Modifies the value of a custom counter. Equivalent to ``set_cc(name, get_cc(name) + value, strict)``.
        """
        return self.set_cc(name, self.get_cc(name) + val, strict)

    def delete_cc(self, name):
        """
        Deletes a custom counter.

        :param str name: The name of the custom counter to delete.
        :raises: :exc:`ConsumableException` if the counter does not exist.
        """
        to_delete = self._get_consumable(name)
        self._character.consumables.remove(to_delete)

    def create_cc_nx(self, name: str, minVal: str = None, maxVal: str = None, reset: str = None,
                     dispType: str = None, reset_to: str = None, reset_by: str = None,
                     title: str = None, desc: str = None):
        """
        Creates a custom counter if one with the given name does not already exist.
        Equivalent to:

        >>> if not cc_exists(name):
        >>>     create_cc(name, minVal, maxVal, reset, dispType, reset_to, reset_by, title, desc)
        """
        if minVal is not None:
            minVal = str(minVal)
        if maxVal is not None:
            maxVal = str(maxVal)
        if reset is not None:
            reset = str(reset)
        if dispType is not None:
            dispType = str(dispType)
        if reset_to is not None:
            reset_to = str(reset_to)
        if reset_by is not None:
            reset_by = str(reset_by)
        if title is not None:
            title = str(title)
        if desc is not None:
            desc = str(desc)

        if not self.cc_exists(name):
            new_consumable = player_api.CustomCounter.new(
                self._character, name, minVal, maxVal, reset, dispType,
                title=title, desc=desc, reset_to=reset_to, reset_by=reset_by)
            self._character.consumables.append(new_consumable)
            self._consumables = None  # reset cache
            return AliasCustomCounter(new_consumable)

    def create_cc(self, name: str, *args, **kwargs):
        """
        Creates a custom counter. If a counter with the same name already exists, it will replace it.

        :param str name: The name of the counter to create.
        :param str minVal: The minimum value of the counter. Supports :ref:`cvar-table` parsing.
        :param str maxVal: The maximum value of the counter. Supports :ref:`cvar-table` parsing.
        :param str reset: One of ``'short'``, ``'long'``, ``'hp'``, ``'none'``, or ``None``.
        :param str dispType: Either ``None`` or ``'bubble'``.
        :param str reset_to: The value the counter should reset to. Supports :ref:`cvar-table` parsing.
        :param str reset_by: How much the counter should change by on a reset. Supports dice but not cvars.
        :param str title: The title of the counter.
        :param str desc: The description of the counter.
        :rtype: AliasCustomCounter
        :returns: The newly created counter.
        """
        if self.cc_exists(name):
            self.delete_cc(name)
        return self.create_cc_nx(name, *args, **kwargs)

    def cc_exists(self, name):
        """
        Returns whether a custom counter exists.

        :param str name: The name of the custom counter to check.
        :returns: Whether the counter exists.
        """
        name = str(name)
        return name in [con.name for con in self._character.consumables]

    def cc_str(self, name):
        """
        Returns a string representing a custom counter.

        :param str name: The name of the custom counter to get.
        :returns: A string representing the current value, maximum, and minimum of the counter.
        :rtype: str
        :raises: :exc:`ConsumableException` if the counter does not exist.

        Example:

        >>> cc_str("Ki")
        '11/17'
        >>> cc_str("Bardic Inspiration")
        '◉◉◉〇〇'
        """
        return str(self._get_consumable(name))

    # --- cvars ---
    @property
    def cvars(self):
        """
        Returns a dict of cvars bound on this character.

        :rtype: dict
        """
        return self._character.cvars.copy()

    def set_cvar(self, name, val: str):
        """
        Sets a custom character variable, which will be available in all scripting contexts using this character.
        Binds the value to the given name in the current runtime.

        :param str name: The name of the variable to set. Must be a valid identifier and not be in the :ref:`cvar-table`.
        :param str val: The value to set it to.
        """  # noqa: E501
        name = str(name)
        val = str(val)
        helpers.set_cvar(self._character, name, val)
        # noinspection PyProtectedMember
        self._interpreter._names[name] = val

    def set_cvar_nx(self, name, val: str):
        """
        Sets a custom character variable if it is not already set.

        :param str name: The name of the variable to set. Must be a valid identifier and not be in the :ref:`cvar-table`.
        :param str val: The value to set it to.
        """  # noqa: E501
        name = str(name)
        if name not in self._character.cvars:
            self.set_cvar(name, val)

    def delete_cvar(self, name):
        """
        Deletes a custom character variable. Does nothing if the cvar does not exist.

        .. note::
            This method does not unbind the name in the current runtime.

        :param str name: The name of the variable to delete.
        """
        name = str(name)
        if name in self._character.cvars:
            del self._character.cvars[name]

    # --- other properties ---
    @cached_property
    def death_saves(self):
        """
        Returns the character's death saves.

        :rtype: AliasDeathSaves
        """
        return AliasDeathSaves(self._character.death_saves)

    @cached_property
    def actions(self):
        """
        The character's actions. These do not include attacks - see the ``attacks`` property.

        :rtype: list[AliasAction]
        """
        return [AliasAction(action, self._character) for action in self._character.actions]

    @property
    def owner(self):
        """
        Returns the id of this character's owner.

        :rtype: int
        """
        return self._character.owner

    @property
    def upstream(self):
        """
        Returns the upstream key for this character.

        :rtype: str
        """
        return self._character.upstream

    @property
    def sheet_type(self):
        """
        Returns the sheet type of this character (beyond, dicecloud, google).

        :rtype: str
        """
        return self._character.sheet_type

    @property
    def race(self):
        """
        Gets the character's race.

        :rtype: str or None
        """
        return self._character.race

    @property
    def background(self):
        """
        Gets the character's background.

        :rtype: str or None
        """
        return self._character.background

    @property
    def csettings(self):
        """
        Gets a copy of the character's settings dict.

        :rtype: dict
        """
        return self._character.options.dict()

    @property
    def coinpurse(self):
        """
        The coinpurse of the character.

        :rtype: :class:`~aliasing.api.character.AliasCoinpurse`
        """
        if self._coinpurse is None:
            self._coinpurse = AliasCoinpurse(self._character.coinpurse, self._character)
        return self._coinpurse

    # --- private helpers ----
    async def func_commit(self, ctx):
        await self._character.commit(ctx)


class AliasCustomCounter:
    def __init__(self, cc):
        """
        :type cc: cogs5e.models.sheet.player.CustomCounter
        """
        self._cc = cc

    @property
    def name(self):
        """
        Returns the cc's name.

        :rtype: str
        """
        return self._cc.name

    @property
    def title(self):
        """
        Returns the cc's title.

        :rtype: str or None
        """
        return self._cc.title

    @property
    def desc(self):
        """
        Returns the cc's description.

        :rtype: str or None
        """
        return self._cc.desc

    @property
    def value(self):
        """
        Returns the current value of the cc.

        :rtype: int
        """
        return self._cc.value

    @property
    def max(self):
        """
        Returns the maximum value of the cc, or 2^31-1 if the cc has no max.

        :rtype: int
        """
        return self._cc.get_max()

    @property
    def min(self):
        """
        Returns the minimum value of the cc, or -2^31 if the cc has no min.

        :rtype: int
        """
        return self._cc.get_min()

    @property
    def reset_on(self):
        """
        Returns the condition on which the cc resets. ('long', 'short', 'none', None)

        :rtype: str or None
        """
        return self._cc.reset_on

    @property
    def display_type(self):
        """
        Returns the cc's display type. (None, 'bubble')

        :rtype: str
        """
        return self._cc.display_type

    @property
    def reset_to(self):
        """
        Returns the value the cc resets to, if it was created with an explicit ``resetto``.

        :rtype: int or None
        """
        return self._cc.get_reset_to()

    @property
    def reset_by(self):
        """
        Returns the amount the cc changes by on a reset, if it was created with an explicit ``resetby``.

        :return: The amount the cc changes by. Guaranteed to be a rollable string.
        :rtype: str or None
        """
        return self._cc.reset_by

    def set(self, new_value, strict=False):
        """
        Sets the cc's value to a new value.

        :param int new_value: The new value to set.
        :param bool strict: Whether to error when going out of bounds (true) or to clip silently (false).
        :return: The cc's new value.
        :rtype: int
        """
        return self._cc.set(int(new_value), strict)

    def reset(self):
        """
        Resets the cc to its reset value. Errors if the cc has no reset value or no reset.

        The reset value is calculated in 3 steps:
        - if the cc has a ``reset_to`` value, it is reset to that
        - else if the cc has a ``reset_by`` value, it is modified by that much
        - else the reset value is its max

        :return CustomCounterResetResult: (new_value: int, old_value: int, target_value: int, delta: str)
        """
        return self._cc.reset()

    def full_str(self, include_name: bool = False):
        """
        Returns a string representing the full custom counter.

        :param bool include_name: If the name of the counter should be included. Defaults to False.
        :returns: A string representing all components of the counter.
        :rtype: str

        Example:

        >>> full_str()
        "◉◉◉◉\\n"
        "**Resets On**: Long Rest"
        >>> full_str(True)
        "**Bardic Inspiration**\\n"
        "◉◉◉◉\\n"
        "**Resets On**: Long Rest"
        """
        out = self._cc.full_str()
        if include_name:
            out = f'**{self.name}**\n' + out
        return out

    def __str__(self):
        return str(self._cc)

    def __repr__(self):
        return f"<AliasCustomCounter name={self.name} value={self.value} max={self.max} min={self.min} " \
               f"title={self.title} desc={self.desc} display_type={self.display_type} " \
               f"reset_on={self.reset_on} reset_to={self.reset_to} reset_by={self.reset_by}>"


class AliasDeathSaves:
    def __init__(self, death_saves):
        """
        :type death_saves: cogs5e.models.sheet.player.DeathSaves
        """
        self._death_saves = death_saves

    @property
    def successes(self):
        """
        Returns the number of successful death saves.

        :rtype: int
        """
        return self._death_saves.successes

    @property
    def fails(self):
        """
        Returns the number of failed death saves.

        :rtype: int
        """
        return self._death_saves.fails

    def succeed(self, num=1):
        """
        Adds one or more successful death saves.

        :param int num: The number of successful death saves to add.
        """
        self._death_saves.succeed(int(num))

    def fail(self, num=1):
        """
        Adds one or more failed death saves.

        :param int num: The number of failed death saves to add.
        """
        self._death_saves.fail(int(num))

    def is_stable(self):
        """
        Returns whether or not the character is stable.

        :rtype: bool
        """
        return self._death_saves.is_stable()

    def is_dead(self):
        """
        Returns whether or not the character is dead.

        :rtype: bool
        """
        return self._death_saves.is_dead()

    def reset(self):
        """
        Resets all death saves.
        """
        self._death_saves.reset()

    def __str__(self):
        return str(self._death_saves)

    def __repr__(self):
        return f"<AliasDeathSaves successes={self.successes} fails={self.fails}>"


class AliasAction:
    """
    An action.
    """

    def __init__(self, action, parent_statblock):
        """
        :type action: cogs5e.models.sheet.action.Action
        :type parent_statblock: cogs5e.models.character.Character
        """
        self._action = action
        self._parent_statblock = parent_statblock

    @property
    def name(self):
        """
        The name of the action.

        :rtype: str
        """
        return self._action.name

    @property
    def activation_type(self):
        """
        The activation type of the action (e.g. action, bonus, etc).

        +--------------+-------+
        | Action Type  | Value |
        +==============+=======+
        | Action       | 1     |
        +--------------+-------+
        | No Action    | 2     |
        +--------------+-------+
        | Bonus Action | 3     |
        +--------------+-------+
        | Reaction     | 4     |
        +--------------+-------+
        | Minute       | 6     |
        +--------------+-------+
        | Hour         | 7     |
        +--------------+-------+
        | Special      | 8     |
        +--------------+-------+

        :rtype: int
        """
        return self._action.activation_type.value

    @property
    def activation_type_name(self):
        """
        The name of the activation type of the action. Will be one of:
        "ACTION", "NO_ACTION", "BONUS_ACTION", "REACTION", "MINUTE", "HOUR", "SPECIAL".
        This list of options may expand in the future.

        :rtype: str
        """
        return self._action.activation_type.name

    @cached_property
    def description(self):
        """
        The description of the action as it appears in a non-verbose action list.

        :rtype: str
        """
        return self._action.build_str(caster=self._parent_statblock, snippet=False)

    @cached_property
    def snippet(self):
        """
        The description of the action as it appears in a verbose action list.

        :rtype: str
        """
        return self._action.build_str(caster=self._parent_statblock, snippet=True)

    def __str__(self):
        return f"**{self.name}**: {self.description}"

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name!r} activation_type={self.activation_type!r} " \
               f"activation_type_name={self.activation_type_name!r}>"


class AliasCoinpurse:
    """
    An object holding the coinpurse for the active character.
    """

    def __init__(self, coinpurse, parent_statblock):
        """
        :type coinpurse: cogs5e.models.sheet.coinpurse.Coinpurse
        :type parent_statblock: cogs5e.models.character.Character
        """
        self._coinpurse = coinpurse
        self._parent_statblock = parent_statblock

    def __getattr__(self, item):
        if item.lower() not in ("cp", "sp", "ep", "gp", "pp"):
            raise ValueError(f"{item} is not valid coin.")
        return self._coinpurse.to_dict().get(item.lower())

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __str__(self):
        if self._parent_statblock.options.compact_coins:
            return self._coinpurse.str_styled('compact')
        return str(self._coinpurse)

    def coin_str(self, cointype: str):
        """
        Returns a string representation of the chosen coin type.

        :param str cointype: The type of coin to return
        :rtype str
        """
        if cointype.lower() not in ("compact", "cp", "sp", "ep", "gp", "pp"):
            raise ValueError(f"{cointype} is not valid coin.")
        return self._coinpurse.str_styled(cointype.lower())

    def modify_coins(self, pp: int = 0, gp: int = 0, ep: int = 0, sp: int = 0, cp: int = 0):
        """
        Modifies your coinpurse based on the provided values.

        :param int pp: Platinum Pieces
        :param int gp: Gold Pieces
        :param int ep: Electrum Pieces
        :param int sp: Silver Pieces
        :param int cp: Copper Pieces
        """
        self._coinpurse.update_currency(pp, gp, ep, sp, cp)

    def set_coins(self, pp: int = 0, gp: int = 0, ep: int = 0, sp: int = 0, cp: int = 0):
        """
        Sets your coinpurse to the provided values.

        :param int pp: Platinum Pieces
        :param int gp: Gold Pieces
        :param int ep: Electrum Pieces
        :param int sp: Silver Pieces
        :param int cp: Copper Pieces
        """
        self._coinpurse.set_currency(pp, gp, ep, sp, cp)

    def get_coins(self):
        """
        Returns a dict of your current coinpurse.

        :rtype dict
        """
        return self._coinpurse.to_dict()

    @staticmethod
    def parse(args):
        """
        Parses a user's coin string into a representation of each currency.
        If the user input is a decimal number, assumes gold pieces.
        Otherwise, allows the user to specify currencies in the form '+1gp -2sp 3cp'

        :rtype dict
        """
        return asdict(parse_coin_args(args))
