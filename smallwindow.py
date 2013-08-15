# Copyright fossfreedom <foss.freedom@gmail.com> 2013
# This is a derivative of the same software name originally created by
# WSID <jongsome@naver.com> 2012
# This program is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
from gi.repository import Peas
from gi.repository import RB
from gi.repository import GLib
from small_rb3compat import ActionGroup
from small_rb3compat import Action
from small_rb3compat import ApplicationShell
from small_rb3compat import is_rb3

import rb

ui_string = \
"""<ui>
	<menubar name="MenuBar">
		<menu name="ViewMenu" action="View">
			<placeholder name="ViewMenuModePlaceholder">
				<menuitem name="SmallWindowMenuItem" action="SmallWindow"/>
			</placeholder>
		</menu>
	</menubar>
</ui>"""


class SmallWindow (GObject.Object, Peas.Activatable):
    object = GObject.Property (type=GObject.Object)
    
    # Builder releated utility functions... ####################################
    
    def load_builder_content(self, builder):
        if( not hasattr( self, "__builder_obj_names" ) ):
            self.__builder_obj_names = list()
    
        for obj in builder.get_objects():
            if( isinstance( obj, Gtk.Buildable ) ):
                name = Gtk.Buildable.get_name(obj).replace(' ', '_')
                self.__dict__[ name ] = obj
                self.__builder_obj_names.append( name )

    def connect_builder_content( self, builder ):
        builder.connect_signals_full( self.connect_builder_content_func, self )

    def connect_builder_content_func( self,
                                      builder,
                                      object,
                                      sig_name,
                                      handler_name,
                                      conn_object,
                                      flags,
                                      target ):
        handler = None
        
        h_name_internal = "_sh_" + handler_name.replace(" ", "_")
    
        if( hasattr( target, h_name_internal ) ):
            handler = getattr( target, h_name_internal )
        else:
            handler = eval(handler_name)
        
        object.connect( sig_name, handler )

    def purge_builder_content( self ):
        for name in self.__builder_obj_names:
            o = self.__dict__[ name ]
            if( isinstance( o, Gtk.Widget ) ):
                o.destroy()
            del self.__dict__[ name ]
    
        del self.__builder_obj_names
    
    # Plugins Methods... #######################################################
    
    def __init__(self):
        super(SmallWindow, self).__init__()
    
    def do_activate(self):
        # Basic Activation Procedure
        self.shell = self.object
        self.main_window = self.shell.props.window
        
        # Prepare internal variables
        self.song_duration = 0
        self.cover_pixbuf = None
        self.entry = None
        
        # Prepare Album Art Displaying
        self.album_art_db = GObject.new( RB.ExtDB, name="album-art" )

        # Build up actions.
        self.action_group = ActionGroup(self.shell, 'small window actions')
        action = self.action_group.add_action(
            func=self.small_window_action,
            action_name='SmallWindow', 
            label='Small Window',
            action_type='app')

        self._appshell = ApplicationShell(self.shell)
        self._appshell.insert_action_group(self.action_group)
        self._appshell.add_app_menuitems(ui_string, 'small window actions')
        
        # Build up small window interface
        builder = Gtk.Builder()
        builder.add_from_file( rb.find_plugin_file( self, "interface.ui" ) )
        self.load_builder_content( builder )
        self.connect_builder_content( builder )
        restore = builder.get_object('restore button')
        restore.connect('clicked', self.main_window_action)
        
        # Prepare windows
        for sub_widget in self.small_window:
            sub_widget.show_all()
        
        geometry = Gdk.Geometry()
        
        geometry.min_width = 300
        geometry.max_width = 5120
        geometry.min_height = -1
        geometry.max_height = -1
        
        self.small_window.set_geometry_hints( self.small_window,
            geometry,
            Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE )

        if is_rb3():
            self.shell.props.application.add_window(self.small_window)
            # Bring Builtin Actions to plugin
            for (a, b) in ((self.play_button, "play"),
                           (self.prev_button, "play-previous"),
                           (self.next_button, "play-next"),
                           (self.repeat_toggle, "play-repeat"),
                           (self.shuffle_toggle, "play-shuffle")):
                a.set_action_name("app." + b)
                if b == "play-repeat" or b == "play-shuffle":
                    a.set_action_target_value(GLib.Variant("b", True))
        else:
            # Bring Builtin Actions to plugin
            for (a, b) in ((self.play_button, "ControlPlay"),
                           (self.prev_button, "ControlPrevious"),
                           (self.next_button, "ControlNext"),
                           (self.repeat_toggle, "ControlRepeat"),
                           (self.shuffle_toggle, "ControlShuffle")):
                a.set_related_action( self._appshell.get_action( "MainActions", b ))
                
        # Bind needed properites.
        self.bind_title = GObject.Binding(  source = self.main_window,
                                            source_property = "title",
                                            target = self.small_window,
                                            target_property = "title",
                                            flags = GObject.BindingFlags.DEFAULT )
        
        # Connect signal handlers to rhythmbox
        self.shell_player = self.shell.props.shell_player
        self.sh_psc = self.shell_player.connect("playing-song-changed",
                                                self._sh_on_song_change )
        
        self.sh_op = self.shell_player.connect("elapsed-changed",
                                                self._sh_on_playing )
    
    def do_deactivate(self):
        self.shell_player.disconnect( self.sh_op )
        self.shell_player.disconnect( self.sh_psc )
        del self.shell_player
        
        del self.bind_title
        self._appshell.cleanup()
        del self.album_art_db
        
        self.purge_builder_content()
        
        del self.main_window
        del self.shell
    
    # Controlling Functions ####################################################
    
    def display_song(self, entry):
        self.entry = entry
        
        self.cover_pixbuf = None
        self.album_cover.clear()
        
        if( entry is None ):
            self.song_button_label.set_text( "" )
        
        else:
            self.song_button_label.set_markup(
                "<b>{title}</b> <small>{album} - {artist}</small>".format(
                title = entry.get_string( RB.RhythmDBPropType.TITLE ),
                album = entry.get_string( RB.RhythmDBPropType.ALBUM ),
                artist = entry.get_string( RB.RhythmDBPropType.ARTIST ) ) )
            
            key = entry.create_ext_db_key( RB.RhythmDBPropType.ALBUM )
            self.album_art_db.request( key,
                                       self.display_song_album_art_callback,
                                       entry )
    
    def display_song_album_art_callback( self, key, filename, data, entry ):
        if( ( data is not None ) and ( isinstance( data, GdkPixbuf.Pixbuf ) ) ):
            self.cover_pixbuf = data
            scale_cover = self.cover_pixbuf.scale_simple( 24, 24,
                                                          GdkPixbuf.InterpType.HYPER )
            
            self.album_cover.set_from_pixbuf( scale_cover )
        else:
            self.cover_pixbuf = None
            self.album_cover.clear()
    
    # Signal Handlers ##########################################################
    
    def small_window_action(self, *args):
        self.main_window.hide()
        self.small_window.show()
    
    def main_window_action(self, *args):
        self.small_window.hide()
        self.main_window.show()
    
    def _sh_small_window_on_close(self, window, asdf):
        self.shell.quit()
    
    def _sh_on_song_change(self, player, entry):
        if( entry is not None ):
            self.song_duration = entry.get_ulong( RB.RhythmDBPropType.DURATION )
        else:
            self.song_duration = 0
        self.display_song(entry)
    
    def _sh_on_playing(self, player, second ):
        if( self.song_duration != 0 ):
            self.song_progress.progress = float(second) / self.song_duration
        
    def _sh_progress_control( self, progress, fraction ):
        if( self.song_duration != 0 ):
            self.shell_player.set_playing_time( self.song_duration * fraction )
    
    def _sh_bigger_cover( self, cover, x, y, key, tooltip ):
        if( self.cover_pixbuf is not None ):
            tooltip.set_icon( self.cover_pixbuf.scale_simple( 300, 300,
                                                          GdkPixbuf.InterpType.HYPER ) )
            return True
        else:
            return False

################################################################################
# Custom Widgets ###############################################################

class SmallProgressBar( Gtk.DrawingArea ):
    
    __gsignals__ = {
        "control": (GObject.SIGNAL_RUN_LAST, None, (float,))
    }
    
    @GObject.Property
    def progress( self ):
        return self.__progress__
    
    @progress.setter
    def progress( self, value ):
        self.__progress__ = value
        self.queue_draw()
    
    def __init__( self ):
        super( SmallProgressBar, self).__init__()
        self.add_events( Gdk.EventMask.POINTER_MOTION_MASK |
                         Gdk.EventMask.BUTTON_PRESS_MASK |
                         Gdk.EventMask.BUTTON_RELEASE_MASK )
        self.button_pressed = False
        self.button_time = 0
        self.__progress__ = 0
    
    def do_draw( self, cc ):
        alloc = self.get_allocation()
        sc = self.get_style_context()
        fgc = sc.get_color( self.get_state_flags() )
        
        cc.set_source_rgba(1, 1, 1, 1 )
        cc.rectangle(0, 0, alloc.width, alloc.height )
        cc.fill()
        
        cc.set_source_rgba( fgc.red, fgc.green, fgc.blue, fgc.alpha )
        cc.rectangle(0, 0, alloc.width * self.progress, alloc.height )
        cc.fill()
        
    def do_motion_notify_event( self, event ):
        if( self.button_pressed ):
            self.control_by_event( event )
            return True
        else:
            return False
    
    def do_button_press_event( self, event ):
        self.button_pressed = True
        self.control_by_event( event )
        return True
    
    def do_button_release_event( self, event ):
        self.button_pressed = False
        self.control_by_event( event )
        return True
    
    def control_by_event( self, event ):
        allocw = self.get_allocated_width()
        fraction = event.x / allocw
        if( self.button_time + 100 < event.time ):
            self.button_time = event.time
            self.emit( "control", fraction )
