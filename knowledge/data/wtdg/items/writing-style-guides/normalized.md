# Style Guides — Write the Docs

Style Guides — Write the Docs
Berlin 2026 CFP is open!
Submit your talk
.
Home
»
Software documentation guide
»
Style Guides
¶
A style guide contains a set of standards for writing and designing content. It helps maintain a consistent style, voice, and tone across your documentation, whether you’re a lone writer or part of a huge docs team. A style guide saves documentarians time and trouble by providing a single reference for writing about common topics, features, and more. It can provide guidelines for different documentation deliverables, such as API reference manuals, tutorials, release notes, or overviews of complex technical concepts.
A consistent tone and style makes your content easier to read, reducing your users’
cognitive load
and increasing their confidence in the content’s authority.
Structure of this page
¶
General style guide information and examples
Writing for accessibility
Including anti-bias information in style guides
Style guides and resources for specific content formats
Write your own style guide?
¶
A style guide can be something as simple as a list of decisions you’ve made about how to refer to different items you frequently write about. Or it can be as complicated as the mighty tomes of major publication houses.
You can certainly create a style guide of your own. For the sake of simplicity, this approach might work if you’re a lone writer or just starting a small docs group. But neither software nor its documentation operates in a vacuum, so it’s a good idea to consult other resources as well. Working from an existing style guide can also help you figure out which things matter in your style guide.
How-to articles for writing a style guide
¶
Creative Blog — Create a website style guide
Gather Content — Developing a Content style guide
HubSpot — How to Create a Writing style guide Built for the Web
Meet Content — Editorial Style for the Web
Techwhirl – Developing a Style Guide for Technical Publications
Traditional writing style guide resources
¶
Style guides have been around for as long as people have been publishing in any format. Traditional style guides originally intended for specific forms of print publication have become basic standards for many others to refer to, including documentarians:
The
AP Stylebook
The
Chicago Manual of Style
Additional books on writing:
The Sense of Style
Stylish Academic Writing
Sample writing guides
¶
Classics for software documentation include:
Apple Style Guide
Microsoft Writing Style Guide
More enterprise software style guides
¶
Google developer documentation
The Red Hat Style Guide
Salesforce
Rackspace
Mailchimp
Quickbooks
Intuit
Adobe
Style guides from government and education
¶
18F Content Guide
Writing for gov.uk
Princeton Editorial Style Guide
Federal Plain Language Style Guide
Style guides from open source projects
¶
Open SUSE Style Guide
gnome Style Guide
Write the Docs Official Website Style Guide
Thinking about accessibility and bias
¶
It’s important to consider accessibility and biases in your style guide to ensure that all readers can understand the content you produce. For details, see:
Accessibility guidelines
Reducing bias in your writing
Avoiding animal-violence idioms
¶
Figurative idioms that reference violence toward animals are worth flagging in your style guide. They often confuse non-native English speakers and can be easily replaced with clearer alternatives at no cost to meaning.
Instead of
Use
“kill two birds with one stone”
“accomplish two things at once”
“beat a dead horse”
“belabor the point”
“more than one way to skin a cat”
“more than one way to do this”
Note: established technical terms that happen to reference animals — such as
kill
(Unix process signal), “canary deployment,” or “monkey-patching” — are out of scope here. These have precise technical meanings and should not be replaced.
Developer documentation and APIs
¶
Style guide and guidelines for code samples:
API reference code comments – Google developer documentation style guide
API Documentation Guidelines – Ruby on Rails
REST API Documentation Best Practices – bocoup
Command line resources
¶
A command-line interface (CLI) processes commands to a computer program in the form of lines of text. Style guide standards for
command line interface
docs and text include these useful CLI resources:
10 design principles for delightful CLIs – Atlassian
CLI Style Guide – Heroku Dev Center
Command Line Interface Guidelines – CLIG
Conventions for writing Linux man pages – die.net
Documenting command-line syntax – Google developer documentation style guide
CLI Docs to Improve DevX video series
gnome Documentation Style Guide
Relevant talk from Write the Docs:
How I Learned to Stop Worrying and Love the Command Line
from WTD Portland 2019
API documentation
¶
Clear, well-formatted, and detailed API documentation is the key for developers to quickly consume and implement your API. It is also key to helping developers understand what happens when an API call is made, and in the case of failure, understand what went wrong and how to fix it.
From the perspective of a user:
If a feature is not documented, it does not exist. If a feature is documented incorrectly, then it is broken.
The best API documentation is often the result of a well
designed API
. Documentation cannot fix a poorly designed API. It is best to work on developing the API and the documentation concurrently.
If your API already exists, automated reference documentation can be useful to document the API in its current state. If your API is still being implemented, API documentation can perform a vital function in the design process.
Documentation-driven design
¶
If your API isn’t built yet, you can create API documentation to help with the design process. The documentation-driven design philosophy comes down to this:
Documentation changes are cheap. Code changes are expensive.
By designing your API through documentation, you can easily get feedback and iterate your design before development begins.
Some API documentation formats have the added benefit of being machine-readable. These formats open the door to a multitude of additional tools that can help during the entire lifecycle of your API:
Create a mock server to help during the initial API design
Test your API before deployment to ensure that the API and the documentation matches
Create interactive documentation that allows developers to perform demo requests to your API
Test-driven documentation
¶
Test-driven documentation aims to improve upon the typical approaches to automated documentation. It allows you to write the bulk of the documentation by hand while also ensuring its accuracy by using your API’s tests to generate some content.
Projects such as
Spring REST Docs
use API tests to generate small snippets of documentation that you can include in the hand-written API documentation. The accuracy of the documentation is ensured by the tests – if the API’s documentation becomes inconsistent with its implementation, the tests that generate the snippets will fail.
API resources
¶
Documenting APIs: a guide for technical writers and engineers – Tom Johnson I’d rather be writing
REST API Guidelines – Microsoft
API Design Guidelines – PayPal
The Ten Essentials for Good API Documentation – A List Apart
Content guidelines
¶
It’s important to create consistency in your content types to manage expectations for what users learn on a given page.
FAQs
¶
Frequently Asked Questions (FAQs) exist to educate and guide users through need-to-know information while pointing them to additional resources when necessary. FAQs are short and limited.
Effective FAQ pages accomplish the following:
Reflects the audience’s needs. This requirement may be derived from understanding search results that lead to the website or documentation.
Regularly updated to reflect the changes in user behavior and data.
Drives users to different parts of the website to deliver more detailed information.
Cover a broader range of topics that may not otherwise warrant individual pages or pieces of content.
Caveat: Be sure to follow a maintenance plan for FAQs, since many content gets parked here and becomes outdated. Consider finding a relevant content structure for the content outside of the FAQ scope.
Release notes
¶
Release notes exist to provide users with vital information required to continue to use and benefit from a product. Release notes content is related to new or updated feature releases. Release notes should be brief, linking out to more details as necessary.
Consider the following when creating an entry for your release notes:
What is the specific change?
Why did we make this change? Why is it important to our users?
Improvement in workflow or UI
Consistency and feature parity
Policy and legal changes
Security
What is the goal for our users who use this feature?
Do our users have all the information they need to move forward?
Is there an additional article for users to read and to learn more? Yes? Link to those resources.
Would an image be beneficial to help users understand this release?
What stakeholders have to approve this content? Does it require the legal team’s approval?
Release Notes Style Guide Resources:
5 excellent product release note examples and how to write your own – Appcues
How to make release notes count – Opensource
How to Write Release Notes Your Users Will Actually Read – ProductPlan
Release notes guidelines – Rackspace
Release notes and changelogs – Unity Docs Style Guide
The Importance of Writing Release Notes – Testlodge
Transforming Your Release Notes into Product Announcements – Parlor
The art of writing great release notes – UX Collective
The art of writing Release Notes A guide, examples & template – Slite
The best and the worst app release notes that will inspire you – announcekit
Examples of great release notes:
DataStax DSE
Digital Ocean
Firefox
Google Ad Manager
Jira
MadCap Flare 2021
Slack
teamwork.
Unreal Engine
What to avoid:
App Release Notes Are Getting Stupid – TechCrunch
Release Notes: 13 Mistakes to Avoid When Writing Bugs and Enhancements – klariti.com
Related talks:
Learning to love release notes
from Write the Docs Prague 2018
Rethinking Release Notes
at Write the Docs Australia 2019
Error messages
¶
Errors in software are unavoidable. Users might click a link that turns out to be broken or they might perform an action only to be met with an unexpected outcome. When a user encounters a problem, it’s important to write error messages in a way that doesn’t alienate the user.
Here are a few tips on what makes a good error message:
Provide explicit indication that something has gone wrong.
Write like a human, not a robot.
Don’t blame the user – be humble.
Make the message short and meaningful.
Include precise descriptions of exact problems.
Offer constructive advice on how to fix the problem.
Related resources:
Error Message Guidelines – Microsoft
Error Message Guidelines –- NN Group
How to Write Good Error Messages -– UX Planet
How to write better error messages –- opensource.com
How to write better error messages for databases – PostgreSQL
Write the Docs is a global community of people who care about documentation.
We have a Slack community, conferences on 4 continents, and local meetups!
Quick search
Site Content
Salary Surveys
Software documentation guide
Book Club
Hiring guide
Stay Connected
About Our Organization
Events and Activities
Learning Resources
Join our mailing list
Email Address
*
What types of updates would you like?
Monthly Community Newsletter
North American Conference Announcements
European Conference Announcements
Australian Conference Announcements
Atlantic Conference Announcements
Missing something?
You can always contribute to our guide on
GitHub
.
© Write the Docs
Contact Us
|
Site map
|
GitHub
|
Twitter
|
LinkedIn
|
Code of Conduct
|
Read the Docs
Website Hosting
Sponsorship Info
