"""
Base keyboard builder class.
"""
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from typing import Optional, List, Dict, Any, Union

from src.bot.keyboards.utils import create_callback_data, format_button_text


class KeyboardBuilder:
    """
    Base class for building inline keyboards with common methods.
    """
    
    def __init__(self):
        """Initialize the keyboard builder with an empty InlineKeyboardBuilder."""
        self.builder = InlineKeyboardBuilder()
        self.button_count = 0
    
    def add_button(self, text: str, callback_data: str, row_width: Optional[int] = None) -> 'KeyboardBuilder':
        """
        Add a button to the keyboard.
        
        Args:
            text: Button text.
            callback_data: Callback data for button.
            row_width: Optional row width for adjusting after adding this button.
            
        Returns:
            Self for method chaining.
        """
        self.builder.add(InlineKeyboardButton(
            text=text,
            callback_data=callback_data
        ))
        self.button_count += 1
        
        if row_width:
            self.builder.adjust(row_width)
            
        return self
    
    def add_main_menu_button(self) -> 'KeyboardBuilder':
        """
        Add a main menu button to the keyboard.
        
        Returns:
            Self for method chaining.
        """
        self.add_button(
            text="🏠 Главное меню",
            callback_data=create_callback_data("menu", "main")
        )
        return self
    
    def add_back_button(self, 
                       to_type: str, 
                       to_id: Optional[str] = None, 
                       custom_text: Optional[str] = None) -> 'KeyboardBuilder':
        """
        Add a back button to the keyboard.
        
        Args:
            to_type: Type to navigate back to (e.g., "accounts", "campaign", "ad").
            to_id: Optional ID of the object to navigate back to.
            custom_text: Optional custom text for the back button.
            
        Returns:
            Self for method chaining.
        """
        # Default texts based on destination type
        text_mapping = {
            "accounts": "↩️ Назад к аккаунтам",
            "account": "↩️ Назад к аккаунту",
            "campaign": "↩️ Назад к кампании",
            "campaigns": "↩️ Назад к кампаниям",
            "ad": "↩️ Назад к объявлению",
            "ads": "↩️ Назад к объявлениям",
            "main": "↩️ Назад в главное меню",
            "cancel": "↩️ Отмена"
        }
        
        text = custom_text or text_mapping.get(to_type, f"↩️ Назад к {to_type}")
        
        if to_type == "cancel":
            callback_data = create_callback_data("back", "cancel")
        elif to_id:
            callback_data = create_callback_data("menu", to_type, to_id)
        else:
            callback_data = create_callback_data("menu", to_type)
        
        self.add_button(text=text, callback_data=callback_data)
        return self
    
    def check_button_parity(self, row_width: int = 2) -> 'KeyboardBuilder':
        """
        Check if number of buttons is even for the given row width.
        Add an empty button if needed to maintain even rows.
        
        Args:
            row_width: Width of rows for button layout.
            
        Returns:
            Self for method chaining.
        """
        if self.button_count % row_width != 0:
            self.add_button(text=" ", callback_data="empty:action")
        return self
    
    def build(self, row_width: Union[int, List[int]] = 2, check_parity: bool = True) -> Any:
        """
        Build the final keyboard markup.
        
        Args:
            row_width: Width of rows or list of widths for button layout.
            check_parity: Whether to check and fix button parity.
            
        Returns:
            InlineKeyboardMarkup ready to be sent with a message.
        """
        if check_parity and isinstance(row_width, int):
            self.check_button_parity(row_width)
            
        if isinstance(row_width, list):
            self.builder.adjust(*row_width)
        else:
            self.builder.adjust(row_width)
            
        return self.builder.as_markup() 