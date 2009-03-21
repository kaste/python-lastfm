#!/usr/bin/env python
"""Module containting the decorators used in the package"""

__author__ = "Abhinav Sarkar <abhinav@abhinavsarkar.net>"
__version__ = "0.2"
__license__ = "GNU Lesser General Public License"
__package__ = "lastfm"

def top_property(list_property_name):
    """
    A decorator to return a property that returns the first value of list 
    attribute corresponding to the provided list property name.
    
    For example, if the list property is top_albums, then the decorator returns
    a property that returns the first (top most) album.
    
    @param list_property_name: the name of the list property. Like 'top_albums'.
    @type list_property_name:  L{str}
    
    @return:                   a property that returns the first value of list attribute 
                               corresponding to the provided list property name
    @rtype:                    L{property}
    """    
    def decorator(func):
        def wrapper(ob):
            top_list = getattr(ob, list_property_name)
            return (len(top_list) and top_list[0] or None)
        return property(fget = wrapper, doc = func.__doc__)
    return decorator

def cached_property(func):
    """
    A decorator to cache the atrribute of the object. When called for the first time,
    the value of the attribute is retrived and saved in an instance variable. Later
    calls return the copy of the cached value, so that the original cached value
    cannot be modified.
    
    @param func:  the getter function of the attribute
    @type func:   C{function}
    
    @return:      a property that wraps the getter function of the attribute
    @rtype:       L{property}
    """
    func_name = func.func_code.co_name
    attribute_name = "_%s" % func_name

    def wrapper(ob):
        cache_attribute = getattr(ob, attribute_name, None)
        if cache_attribute is None:
            cache_attribute = func(ob)
            setattr(ob, attribute_name, cache_attribute)
        try:
            cp = copy.copy(cache_attribute)
            return cp
        except LastfmError:
            return cache_attribute

    return property(fget = wrapper, doc = func.__doc__)

def authenticate(func):
    """
    A decorator to check if the current user is authenticated or not. Used only
    on the functions that need authentication. If not authenticated then an
    exception is raised.
    
    @param func:    a function that needs to be authentication, for being called
    @type func:     C{function}
    
    @return:        a function that wraps the original function
    @rtype:         C{function}
    
    @raise AuthenticationFailedError: If the user is not authenticated, then an
                                      exception is raised.
    """
    def wrapper(self, *args, **kwargs):
        from lastfm.user import User, Api
        username = None
        if isinstance(self, User):
            username = self.name
            if self.authenticated:
                return func(self, *args, **kwargs)
        elif hasattr(self, 'user'):
            username = self.user.name
            if self.user.authenticated:
                return func(self, *args, **kwargs)
        elif hasattr(self, '_subject') and isinstance(self._subject, User):
            username = self._subject.name
            if self._subject.authenticated:
                return func(self, *args, **kwargs)
        elif hasattr(self, '_api') and isinstance(self._api, Api):
            try:
                user = self._api.get_authenticated_user()
                username = user.name
                return func(self, *args, **kwargs)
            except AuthenticationFailedError:
                pass
        raise AuthenticationFailedError(
            "user '%s' does not have permissions to access the service" % username)
    wrapper.__doc__ = func.__doc__
    return wrapper

def depaginate(func):
    """
    A decorator to depaginate the search results.
    
    @param func:    a function that returns the first page of search results
    @type func:     C{function}
    
    @return:        a function that wraps the original function and returns
                    a L{lazylist} of all search results (all pages)
    @rtype:         C{function}
    """
    from lastfm.lazylist import lazylist
    def wrapper(*args, **kwargs):
        @lazylist
        def generator(lst):
            gen = func(*args, **kwargs)
            total_pages = gen.next()
            for e in gen:
                yield e
            for page in xrange(2, total_pages+1):
                kwargs['page'] = page
                gen = func(*args, **kwargs)
                gen.next()
                for e in gen:
                    yield e
        return generator()
    wrapper.__doc__ = func.__doc__
    return wrapper

def async_callback(func):
    """
    A decorator to convert a synchronous (blocking) function into 
    an asynchronous (non-blocking) function.
    
    Pass a callback function as a keyword argument 
    (C{func(other argument... , callback = callback)}) or positional argument 
    (C{func(other argument... , callback)}) to the function to activate the
    asynchronous behaviour. The callback function is called with the return value
    of the original function when it returns. If an exception is raised in the
    original function, then the callback function is called with that exception.
    If the callback function is not given then the original function is called
    synchronously (it blocks the caller function) and its return value is returned.
    
    All the functions on which this decorator is applied get the signature: 
    C{func(self, *args, **kwargs)}. Refer to the documentation or source code of 
    the original function for the correct function signature.
    
    @param func:    a synchronous (blocking) function
    @type func:     C{function}
    
    @return:        an asynchronous (non-blocking) function that wraps the 
                    original synchronous (blocking) function
    @rtype:         C{function}
    """
    from threading import Thread
    def wrapper(self, *args, **kwargs):
        callback = None
        for a in args:
            if callable(a):
                callback = a
                args = list(args)
                args.remove(a)
                args = tuple(args)
                break
        if 'callback' in kwargs:
            callback = kwargs['callback']
            del kwargs['callback']
            
        if (callback is not None and callable(callback)):
            def async_call():
                result = None
                try:
                    result = func(self, *args, **kwargs)
                except Exception, e:
                    result = e
                callback(result)
            thread = Thread(target = async_call)
            thread.start()
            return
        return func(self, *args, **kwargs)
            
    wrapper.__doc__ = "%s\n        @see: L{async_callback}" % func.__doc__
    return wrapper

def _get_arg_string(argspecs):
    arg_str = ""    
    args = argspecs.args
    args.remove('self')
    defaults = argspecs.defaults
    
    if defaults is not None:
        defargs = args[-len(defaults):]
        nondefargs = args[:-len(defaults)]
        nondefargs_str = ", ".join(nondefargs)
        defargs_str = ", ".join(["%s = %s" % (defargs[i], defaults[i]) for i in xrange(len(defargs))])
        if nondefargs_str != '' and defargs_str != '':
            arg_str = "%s, %s" % (nondefargs_str, defargs_str)
        elif nondefargs_str != '':
            arg_str = nondefargs_str
        elif defargs_str != '':
            arg_str = defargs_str
    else:
        arg_str = ", ".join(args)
    print arg_str
    return arg_str

import copy
from lastfm.error import LastfmError, AuthenticationFailedError