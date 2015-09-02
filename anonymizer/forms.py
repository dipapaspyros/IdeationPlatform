from django import forms
from django.core.exceptions import ValidationError
from mysql.connector import connect as mysql_connect, InterfaceError, ProgrammingError
from anonymizer.lists import AGGREGATE_LIST, PROVIDER_PLUGINS
from models import ConnectionConfiguration

__author__ = 'dipap'


class ConnectionConfigurationForm(forms.ModelForm):
    class Meta:
        model = ConnectionConfiguration
        fields = ['name', 'connection_type']


class Sqlite3ConnectionForm(forms.Form):
    path = forms.CharField()

    def clean(self):
        # default validation
        super(Sqlite3ConnectionForm, self).clean()

        # check that the file already exists -- we don't want to create a new database
        f = None
        ima = ''

        try:
            f = open(self.cleaned_data['path'], 'r')
            ima = f.read(16).encode('hex')
        except IOError, e:
            raise ValidationError(e[1])
        finally:
            # validate that the file is an sqlite3 file
            if f:
                f.close()

        # see http://www.sqlite.org/fileformat.html#database_header magic header string
        if ima != "53514c69746520666f726d6174203300":
            e_str = "Invalid database file"
            self.add_error(None, e_str)
            raise ValidationError(e_str)

        return self.cleaned_data


class MySQLConnectionForm(forms.Form):
    DEFAULT_PORT = '3306'

    host = forms.CharField(max_length=512)
    port = forms.CharField(initial=DEFAULT_PORT)
    user = forms.CharField()
    password = forms.CharField(required=False)
    database = forms.CharField()

    def clean(self):
        # default validation
        super(MySQLConnectionForm, self).clean()

        # test connection
        try:
            mysql_connect(host=self.cleaned_data['host'], port=self.cleaned_data['port'],
                          user=self.cleaned_data['user'], password=self.cleaned_data['password'],
                          database=self.cleaned_data['database'])

        except (InterfaceError, ProgrammingError), e:
            raise ValidationError(str(e))

        return self.cleaned_data


class UserTableSelectionForm(forms.Form):

    def __init__(self, connection, *args, **kwargs):
        super(UserTableSelectionForm, self).__init__(*args, **kwargs)

        # create list with all possible options
        choices = []
        not_suggested = []
        tables = connection.tables()
        for table in tables:
            table_name = table[0]
            if 'user' in table_name.lower():
                choices.append((table_name, table_name + ' (suggested)'),)
            else:
                not_suggested.append(table_name)

        for table in not_suggested:
            choices.append((table, table))

        self.fields['users_table'] = forms.ChoiceField(choices=choices)


class ColumnForm(forms.Form):
    include = forms.BooleanField(initial=True)
    name = forms.CharField()
    c_type = forms.CharField(required=False)
    aggregate = forms.ChoiceField(choices=AGGREGATE_LIST, required=False)

    def __init__(self, all_properties, *args, **kwargs):
        super(ColumnForm, self).__init__(*args, **kwargs)

        choices = []
        for p in all_properties:
            choices.append((p[2], p[0]))

        choices += PROVIDER_PLUGINS

        self.fields['source'] = forms.ChoiceField(choices=choices)