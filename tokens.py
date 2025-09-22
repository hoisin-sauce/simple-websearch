from typing import Generator, Tuple
from nltk.corpus import stopwords
from nltk import PorterStemmer
import nltk
import re
import string

stemmer = PorterStemmer()

nltk.download('stopwords')
nltk.download('punkt')
token_regex_pattern = '|'.join(map(re.escape, string.punctuation))

stopwords = set(stopwords.words('english'))

class Token:
    def __init__(self, token_name: str, token_count: int):
        self.token_name = token_name
        self.token_count = token_count

    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        return self.token_name == other.token_name

    def __hash__(self):
        return hash(self.token_name)

class TokenContainer:
    def __init__(self, tokens: list[Token] | None = None):
        if tokens is None:
            tokens = []
        self._token_dict = {token.token_name: token for i, token in enumerate(tokens)}

    def add_token(self, token: Token) -> None:
        if token.token_name not in self._token_dict:
            self._token_dict[token.token_name] = token
        else:
            self._token_dict[token.token_name].token_count += token.token_count

    def get_token(self, token_name: str) -> Token:
        return self._token_dict[token_name]

    def tokens(self) -> Generator[Token, None, None]:
        for token in self._token_dict:
            yield self._token_dict[token]

    def token_names(self) -> Generator[str, None, None]:
        for token in self._token_dict:
            yield token

    def token_name_tuples(self) -> Generator[Tuple[str], None, None]:
        for token in self._token_dict:
            yield (token,)

    def token_counts(self):
        for token in self._token_dict:
            yield self._token_dict[token].token_count

    def total_tokens(self) -> int:
        return sum(self.token_counts())

    def get_count(self, token_name: str) -> int:
        return self._token_dict[token_name].token_count

    def __len__(self):
        return len(self._token_dict)


def get_tokens(text: str) -> TokenContainer:
    tokens = re.split(r'\W+', text)

    additional_tokens: list[str] = []
    for token in tokens:
        if any(char in string.punctuation for char in token):
            additional_tokens += re.split(token_regex_pattern, token)

    tokens += additional_tokens

    final_tokens: TokenContainer = TokenContainer()

    for token in tokens:
        token = token.lower()
        token = stemmer.stem(token)

        if token in stopwords or not token:
            continue

        token = Token(token, 1)

        final_tokens.add_token(token)

    return final_tokens
