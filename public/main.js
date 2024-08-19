const e = React.createElement;
const b = ReactBootstrap;

class App extends React.Component {
  constructor(props) {
    super(props)
    window.app = this
    this.state = {page: null}
  }

  refresh = async () => {
    this.setState({page: Groups})
  }

  async componentDidMount() {
    await this.refresh()
  }

  render() {
    if (this.state.page == null) {
      return e(b.Spinner, {animation: "border", className: "justify-content-center"})
    }
    return e(this.state.page)
  }
}

class Groups extends React.Component {
  constructor(props) {
    super(props);
    this.state = {groups: []};
    this.active_key = null;
  }

  refresh = async x => {
    let status_res = await fetch('status');
    let status = await status_res.json();
    console.log(status.reqs.length);
    Promise.all(status.reqs.map(async (req) => {
      let res = await fetch('resource', {method: "POST", body: JSON.stringify(req)});
      let msg = await res.json();
      this.setState({groups: this.state.groups.concat(msg)});
    }))
  }

  async componentDidMount() {
    await this.refresh();
  }

  onLoad = (e) => {
  }

  render () {
    if (this.state.groups.length == 0)
      return null;
    let groups = this.state.groups
      .filter(group => group.code == 'ok' && group.res.items != undefined && group.res.items.length>0)
      .map(group => {
        let items = group.res.items
          .map((item, index) => 
            e(b.ListGroupItem, {
              action: true, 
              href: item.link,
              key: index}, item.title));
        if (items.length)
          items.splice(0, 0, e(b.ListGroupItem, {variant: 'primary'}, group.res.title));
        let newGroup = e(b.ListGroup, {horizontal: "md-2", className: "mb-10"}, ...items);
        return e(b.Row, {}, newGroup);
      });

    return e(b.Container, {"data-bs-theme": "dark", fluid: "xxl", className: "box"}, ...groups);
  }
}
    
ReactDOM.createRoot(document.getElementById("root")).render(e(App))