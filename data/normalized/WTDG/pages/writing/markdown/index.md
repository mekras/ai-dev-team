## What is Markdown?

Markdown is a free markup language with simple formatting syntax. Use it for
creating webpages, documents or any text that needs to be transformed into other
formats like HTML.

## Why use Markdown?

It makes it easier for non-tech writers to produce documentation that can be
collaborative and flexible at the same time.

## How to use Markdown

### Formatting text in Markdown

- To format the text, follow these rules:
  - For italics, wrap the item with one star on each side:
    `*one star on each side*`.
    - For bold text, wrap the item with two stars on each side:
      `**two stars on each side**`.
    - For striking through text in GitHub Markdown, wrap the item in two tildes:
      `~~strikethrough~~`.
    - For links, wrap link text in brackets \[ \], and then wrap the URL in
      parentheses ( ):
      `[This text links to WritetheDocs](https://www.writethedocs.org)`.

The formatted text will look like this:

- For italics, wrap the item with one star on each side, like this: _one star on
  each side_.
- For bold letters, wrap the item with two stars on each side: **two stars on
  each side**.
- For striking through text in GitHub Markdown, wrap the item in two tildes:
  ~~strikethrough~~.
- For links, wrap link text in brackets \[ \], and then wrap the URL in
  parentheses ( ):
  [This text links to WritetheDocs](https://www.writethedocs.org/).

### Adding images

Adding images is like adding links. Just add an exclamation mark at the
beginning of the line:

`![alt text](https://pbs.twimg.com/profile_images/556169790587281409/AwkaVrhP_400x400.png).`

The image will look like this:

.

### How to produce lists?

To add a bulleted or unordered list of items:

```
- Just add a dash first and then write a text.
- If you add another dash in the following line, you will have another item in the list.
  - If you add four spaces or use a tab key, you will create an indented list.
    - If you need to insert an indented list within an intended one, just press a tab key again.
```

The formatted text will look like this:

- Just add a dash first and then write a text.
- If you add another dash in the following line, you will have another item in
  the list.
  - If you add four spaces or use a tab key, you will create an indented list.
    - If you need to insert an indented list within an intended one, just press
      a tab key again.

To add a numbered or ordered list of items:

```
1. Just type a number followed by a dot.
2. If you want to add a second item, just type in another number followed by a dot.
1. If you make a mistake when typing numbers, fear not, Markdown will correct it for you.
    1. If you press a tab key or type four spaces, you will get an indented list and the numbering
    will start from scratch.
        1. If you want to insert an indented numbered list within an existing indented numbered one,
        just press the tab key again.
            - If need be, you can also add an indented unordered list within an indented numbered one, and vice versa,
            by pressing a tab key and typing a dash.
```

The formatted text will look like this:

1. Just type a number followed by a dot.
2. If you want to add a second item, just type in another number followed by a
   dot.
3. If you make a mistake when typing numbers, fear not, Markdown will correct it
   for you.
   1. If you press a tab key or type four spaces, you will get an indented list
      and the numbering will start from scratch.
      1. If you want to insert an indented numbered list within an existing
         indented numbered one, just press the tab key again.
         - If need be, you can also add an indented unordered list within an
           indented numbered one, and vice versa, by pressing a tab key and
           typing a dash.

### Horizontal Rule

Create a horizontal rule with three or more hyphens, asterisks, or underscores
on a line:

`---`

`* * *`

`___`

The formatted text will look like this:

---

### Quotes and Code

Add a quotation with the > character at the beginning of each line:

```
> “I make Jessica Simpson look like a rock scientist.”

> —Tara Reid, actress
```

The quote will look like this:

> “I make Jessica Simpson look like a rock scientist.”

> —Tara Reid, actress

And finally, insert code into your text with one apostrophe on each side when
adding code within one line, or with 3 apostrophes opening and closing your code
block, like this:

This line contains \`code\`

This is a code section:

```
\`\`\`
this is code
\`\`\`
```

Which will look like this:

This line contains `code`

This is a code section:

```
this is code
```

You can also “cheat”, adding HTML-formatted text when markdown seems too
limited, but first look at these resources to find solutions:
